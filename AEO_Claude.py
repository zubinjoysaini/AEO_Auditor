# -*- coding: utf-8 -*-
"""
Created on Tue Nov 25 12:12:12 2025

@author: zubin
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urljoin, urlparse
import textstat
import os


app = Flask(__name__)
CORS(app)

def fetch_page(url):
    """Fetch webpage content"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text

def analyze_schema(soup):
    """Analyze structured data/schema markup"""
    schema_scripts = soup.find_all('script', type='application/ld+json')
    
    faq_present = False
    howto_present = False
    article_present = False
    faq_count = 0
    howto_count = 0
    
    for script in schema_scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                for item in data:
                    schema_type = item.get('@type', '').lower()
                    if 'faqpage' in schema_type:
                        faq_present = True
                        faq_count = len(item.get('mainEntity', []))
                    elif 'howto' in schema_type:
                        howto_present = True
                        howto_count = len(item.get('step', []))
                    elif 'article' in schema_type:
                        article_present = True
            else:
                schema_type = data.get('@type', '').lower()
                if 'faqpage' in schema_type:
                    faq_present = True
                    faq_count = len(data.get('mainEntity', []))
                elif 'howto' in schema_type:
                    howto_present = True
                    howto_count = len(data.get('step', []))
                elif 'article' in schema_type:
                    article_present = True
        except:
            continue
    
    return {
        'faq_present': faq_present,
        'faq_count': faq_count,
        'howto_present': howto_present,
        'howto_count': howto_count,
        'article_present': article_present
    }

def analyze_questions(soup):
    """Analyze question-based content"""
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    
    question_words = ['what', 'why', 'how', 'when', 'where', 'who', 'which', 'can', 'is', 'are', 'do', 'does']
    question_headings = []
    
    for heading in headings:
        text = heading.get_text().strip().lower()
        if any(text.startswith(qw) for qw in question_words) or text.endswith('?'):
            question_headings.append(heading.get_text().strip())
    
    return {
        'total_headings': len(headings),
        'question_headings': len(question_headings),
        'question_heading_examples': question_headings[:5]
    }

def analyze_snippet_optimization(soup):
    """Analyze featured snippet readiness"""
    paragraphs = soup.find_all('p')
    first_para_words = 0
    
    if paragraphs:
        first_para_text = paragraphs[0].get_text().strip()
        first_para_words = len(first_para_text.split())
    
    lists = len(soup.find_all(['ul', 'ol']))
    tables = len(soup.find_all('table'))
    
    short_paragraphs = 0
    for p in paragraphs:
        word_count = len(p.get_text().split())
        if 40 <= word_count <= 60:
            short_paragraphs += 1
    
    snippet_score = 0
    if first_para_words >= 40 and first_para_words <= 60:
        snippet_score += 30
    if lists > 0:
        snippet_score += 25
    if tables > 0:
        snippet_score += 20
    if short_paragraphs >= 3:
        snippet_score += 25
    
    return {
        'first_para_words': first_para_words,
        'lists': lists,
        'tables': tables,
        'short_paragraphs': short_paragraphs,
        'snippet_score': min(snippet_score, 100)
    }

def analyze_structure(soup):
    """Analyze content structure"""
    text = soup.get_text()
    
    has_tldr = bool(re.search(r'(tl;?dr|summary|key takeaways)', text, re.IGNORECASE))
    has_toc = bool(soup.find(['div', 'nav'], class_=re.compile('toc|table-of-contents', re.I)))
    
    paragraphs = soup.find_all('p')
    if paragraphs:
        total_words = sum(len(p.get_text().split()) for p in paragraphs)
        avg_para_length = total_words / len(paragraphs)
    else:
        avg_para_length = 0
    
    word_count = len(text.split())
    
    try:
        flesch_score = textstat.flesch_reading_ease(text)
    except:
        flesch_score = 0
    
    return {
        'has_tldr': has_tldr,
        'has_toc': has_toc,
        'avg_para_length': round(avg_para_length, 1),
        'word_count': word_count,
        'flesch_reading_ease': round(flesch_score, 1)
    }

def analyze_entities(soup):
    """Basic entity extraction"""
    text = soup.get_text()
    words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    entities = list(set(words))
    entities_found = len(entities)
    
    return {
        'entities_found': entities_found,
        'entity_examples': entities[:10]
    }

def analyze_eeat(soup, url):
    """Analyze E-E-A-T signals"""
    author_meta = soup.find('meta', attrs={'name': re.compile('author', re.I)})
    has_author_meta = bool(author_meta)
    
    date_meta = soup.find('meta', attrs={'property': re.compile('published', re.I)})
    has_date = bool(date_meta)
    
    has_author_bio = bool(soup.find(['div', 'section'], class_=re.compile('author|bio', re.I)))
    
    links = soup.find_all('a', href=True)
    has_about_link = any('about' in link['href'].lower() for link in links)
    has_contact_link = any('contact' in link['href'].lower() for link in links)
    
    has_sources = bool(soup.find(['div', 'section'], class_=re.compile('reference|source|citation', re.I)))
    
    return {
        'has_author_meta': has_author_meta,
        'has_date': has_date,
        'has_author_bio': has_author_bio,
        'has_about_link': has_about_link,
        'has_contact_link': has_contact_link,
        'has_sources': has_sources
    }

def calculate_score_breakdown(data):
    """Calculate detailed score breakdown by component"""
    breakdown = {}
    
    # Schema Score (25 points)
    schema_score = 0
    if data['schema']['faq_present']:
        schema_score += 10
    if data['schema']['howto_present']:
        schema_score += 10
    if data['schema']['article_present']:
        schema_score += 5
    breakdown['schema'] = {'score': schema_score, 'max': 25}
    
    # Question Content Score (20 points)
    question_score = min(data['questions']['question_headings'] * 4, 20)
    breakdown['questions'] = {'score': question_score, 'max': 20}
    
    # Snippet Optimization Score (20 points)
    snippet_score = data['snippet']['snippet_score'] * 0.2
    breakdown['snippet'] = {'score': round(snippet_score, 1), 'max': 20}
    
    # Structure Score (15 points)
    structure_score = 0
    if data['structure']['has_tldr']:
        structure_score += 5
    if data['structure']['has_toc']:
        structure_score += 5
    if data['structure']['flesch_reading_ease'] >= 60:
        structure_score += 5
    breakdown['structure'] = {'score': structure_score, 'max': 15}
    
    # E-E-A-T Score (10 points)
    eeat_score = sum([
        data['eeat']['has_author_meta'],
        data['eeat']['has_date'],
        data['eeat']['has_author_bio'],
        data['eeat']['has_sources']
    ]) * 2.5
    breakdown['eeat'] = {'score': eeat_score, 'max': 10}
    
    # Entity Score (10 points)
    entity_score = 0
    if data['entities']['entities_found'] > 10:
        entity_score = 10
    elif data['entities']['entities_found'] > 5:
        entity_score = 5
    breakdown['entities'] = {'score': entity_score, 'max': 10}
    
    total_score = sum(item['score'] for item in breakdown.values())
    
    return {
        'breakdown': breakdown,
        'total': min(round(total_score), 100)
    }

def calculate_engine_scores(data):
    """Calculate scores for different AI engines based on their priorities"""
    base_breakdown = calculate_score_breakdown(data)
    
    engines = {
        'ChatGPT': {
            'weights': {
                'schema': 1.2,      # High priority on structured data
                'questions': 1.1,   # Important for conversational queries
                'snippet': 1.0,
                'structure': 1.3,   # Very high on readability
                'eeat': 0.9,
                'entities': 1.0
            },
            'focus': 'Prioritizes conversational structure and clear formatting'
        },
        'Claude': {
            'weights': {
                'schema': 1.0,
                'questions': 1.2,   # High on natural questions
                'snippet': 1.0,
                'structure': 1.4,   # Highest on content quality
                'eeat': 1.3,        # Very high on trustworthiness
                'entities': 1.1
            },
            'focus': 'Emphasizes content quality, trustworthiness, and natural language'
        },
        'Gemini': {
            'weights': {
                'schema': 1.3,      # Very high on structured data
                'questions': 1.0,
                'snippet': 1.2,     # High on snippet optimization
                'structure': 1.0,
                'eeat': 1.0,
                'entities': 1.2     # High on entity recognition
            },
            'focus': 'Strong preference for structured data and entities'
        },
        'Perplexity': {
            'weights': {
                'schema': 1.1,
                'questions': 1.3,   # Very high on Q&A format
                'snippet': 1.2,     # High on concise answers
                'structure': 1.0,
                'eeat': 1.2,        # High on source credibility
                'entities': 1.0
            },
            'focus': 'Optimized for direct answers and source attribution'
        }
    }
    
    engine_scores = {}
    
    for engine_name, config in engines.items():
        weighted_score = 0
        total_weight = 0
        
        for component, values in base_breakdown['breakdown'].items():
            weight = config['weights'].get(component, 1.0)
            weighted_score += (values['score'] / values['max']) * values['max'] * weight
            total_weight += values['max'] * weight
        
        normalized_score = (weighted_score / total_weight) * 100
        engine_scores[engine_name] = {
            'score': min(round(normalized_score, 1), 100),
            'focus': config['focus']
        }
    
    return engine_scores

def generate_prioritized_recommendations(data):
    """Generate recommendations with priority levels"""
    recommendations = []
    
    # HIGH PRIORITY (Critical for most engines)
    if not data['schema']['faq_present']:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Schema Markup',
            'action': "Add FAQ schema markup to target 'People Also Ask' boxes",
            'impact': 'Critical for all answer engines - enables direct answer extraction',
            'effort': 'Medium'
        })
    
    if data['questions']['question_headings'] < 3:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Content Structure',
            'action': 'Add more question-based headings (What, Why, How)',
            'impact': 'Improves discoverability in conversational AI searches',
            'effort': 'Low'
        })
    
    if data['snippet']['first_para_words'] < 40 or data['snippet']['first_para_words'] > 60:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Snippet Optimization',
            'action': 'Optimize first paragraph to 40-60 words for featured snippets',
            'impact': 'Increases chances of being selected as the primary answer',
            'effort': 'Low'
        })
    
    # MEDIUM PRIORITY (Important but not critical)
    if not data['eeat']['has_author_meta']:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'E-E-A-T',
            'action': 'Add author information and credentials',
            'impact': 'Builds trust signals, especially important for Claude and Perplexity',
            'effort': 'Low'
        })
    
    if not data['schema']['howto_present'] and any('how' in str(q).lower() for q in data['questions'].get('question_heading_examples', [])):
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Schema Markup',
            'action': 'Add HowTo schema for step-by-step content',
            'impact': 'Enhances visibility for process-oriented queries',
            'effort': 'Medium'
        })
    
    if data['snippet']['lists'] == 0:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Content Format',
            'action': 'Add bulleted or numbered lists for better snippet visibility',
            'impact': 'Makes content easier to extract and cite',
            'effort': 'Low'
        })
    
    if not data['structure']['has_tldr']:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Content Structure',
            'action': 'Add a TL;DR or summary section at the beginning',
            'impact': 'Provides quick answer extraction point',
            'effort': 'Medium'
        })
    
    # LOW PRIORITY (Nice to have)
    if data['structure']['avg_para_length'] > 100:
        recommendations.append({
            'priority': 'LOW',
            'category': 'Readability',
            'action': 'Break down paragraphs into shorter chunks (2-3 sentences)',
            'impact': 'Improves readability scores and scannability',
            'effort': 'Medium'
        })
    
    if data['entities']['entities_found'] < 10:
        recommendations.append({
            'priority': 'LOW',
            'category': 'Semantic SEO',
            'action': 'Include more relevant entities and topics for semantic richness',
            'impact': 'Helps with entity recognition, especially for Gemini',
            'effort': 'High'
        })
    
    if not data['eeat']['has_sources']:
        recommendations.append({
            'priority': 'LOW',
            'category': 'E-E-A-T',
            'action': 'Add references and citations to external sources',
            'impact': 'Strengthens credibility and fact-checking',
            'effort': 'Medium'
        })
    
    if not data['structure']['has_toc']:
        recommendations.append({
            'priority': 'LOW',
            'category': 'Navigation',
            'action': 'Add a table of contents for long-form content',
            'impact': 'Improves content navigation and structure signals',
            'effort': 'Low'
        })
    
    # Sort by priority
    priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    recommendations.sort(key=lambda x: priority_order[x['priority']])
    
    return recommendations

@app.route('/api/aeo-analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Fetch page
        html = fetch_page(url)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Run all analyses
        schema_data = analyze_schema(soup)
        question_data = analyze_questions(soup)
        snippet_data = analyze_snippet_optimization(soup)
        structure_data = analyze_structure(soup)
        entity_data = analyze_entities(soup)
        eeat_data = analyze_eeat(soup, url)
        
        # Combine results
        result = {
            'url': url,
            'schema': schema_data,
            'questions': question_data,
            'snippet': snippet_data,
            'structure': structure_data,
            'entities': entity_data,
            'eeat': eeat_data
        }
        
        # Calculate scores
        score_breakdown = calculate_score_breakdown(result)
        engine_scores = calculate_engine_scores(result)
        recommendations = generate_prioritized_recommendations(result)
        
        # Flatten for frontend compatibility
        flattened = {
            'url': url,
            'aeo_score': score_breakdown['total'],
            'score_breakdown': score_breakdown['breakdown'],
            'engine_scores': engine_scores,
            'faq_schema_present': schema_data['faq_present'],
            'faq_count': schema_data['faq_count'],
            'howto_schema_present': schema_data['howto_present'],
            'howto_count': schema_data['howto_count'],
            'article_schema_present': schema_data['article_present'],
            'total_headings': question_data['total_headings'],
            'question_headings': question_data['question_headings'],
            'question_heading_examples': question_data['question_heading_examples'],
            'first_para_words': snippet_data['first_para_words'],
            'lists': snippet_data['lists'],
            'tables': snippet_data['tables'],
            'short_paragraphs': snippet_data['short_paragraphs'],
            'snippet_score': snippet_data['snippet_score'],
            'has_tldr': structure_data['has_tldr'],
            'has_toc': structure_data['has_toc'],
            'word_count': structure_data['word_count'],
            'flesch_reading_ease': structure_data['flesch_reading_ease'],
            'entities_found': entity_data['entities_found'],
            'entity_examples': entity_data['entity_examples'],
            'has_author_meta': eeat_data['has_author_meta'],
            'has_date': eeat_data['has_date'],
            'has_author_bio': eeat_data['has_author_bio'],
            'has_about_link': eeat_data['has_about_link'],
            'has_contact_link': eeat_data['has_contact_link'],
            'has_sources': eeat_data['has_sources'],
            'recommendations': recommendations,
            'aeo_checks': {
                'FAQ Schema': schema_data['faq_present'],
                'HowTo Schema': schema_data['howto_present'],
                'Question Headings': question_data['question_headings'] >= 3,
                'Snippet Ready': snippet_data['snippet_score'] >= 50,
                'Has TL;DR': structure_data['has_tldr'],
                'Good Readability': structure_data['flesch_reading_ease'] >= 60,
                'Author Info': eeat_data['has_author_meta']
            }
        }
        
        return jsonify(flattened)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'tool': 'AEO On-Page Auditor'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"=== Starting Flask on port {port} ===")
    app.run(host='0.0.0.0', port=port, debug=False)