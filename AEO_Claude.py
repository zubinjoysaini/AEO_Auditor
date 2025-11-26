import streamlit as st
import requests
from beautifulsoup4 import BeautifulSoup
import re
import json
import textstat

st.set_page_config(
    page_title="AEO On-Page Auditor",
    page_icon="🎯",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #4F46E5;
        margin-bottom: 1rem;
    }
    .score-card {
        padding: 2rem;
        border-radius: 1rem;
        text-align: center;
        margin: 1rem 0;
    }
    .score-high {
        background-color: #D1FAE5;
        color: #065F46;
    }
    .score-medium {
        background-color: #FEF3C7;
        color: #92400E;
    }
    .score-low {
        background-color: #FEE2E2;
        color: #991B1B;
    }
    .metric-card {
        padding: 1rem;
        background-color: #F9FAFB;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .priority-high {
        border-left: 4px solid #DC2626;
        background-color: #FEF2F2;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
    }
    .priority-medium {
        border-left: 4px solid #F59E0B;
        background-color: #FFFBEB;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
    }
    .priority-low {
        border-left: 4px solid #3B82F6;
        background-color: #EFF6FF;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

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
    
    schema_score = 0
    if data['schema']['faq_present']:
        schema_score += 10
    if data['schema']['howto_present']:
        schema_score += 10
    if data['schema']['article_present']:
        schema_score += 5
    breakdown['schema'] = {'score': schema_score, 'max': 25}
    
    question_score = min(data['questions']['question_headings'] * 4, 20)
    breakdown['questions'] = {'score': question_score, 'max': 20}
    
    snippet_score = data['snippet']['snippet_score'] * 0.2
    breakdown['snippet'] = {'score': round(snippet_score, 1), 'max': 20}
    
    structure_score = 0
    if data['structure']['has_tldr']:
        structure_score += 5
    if data['structure']['has_toc']:
        structure_score += 5
    if data['structure']['flesch_reading_ease'] >= 60:
        structure_score += 5
    breakdown['structure'] = {'score': structure_score, 'max': 15}
    
    eeat_score = sum([
        data['eeat']['has_author_meta'],
        data['eeat']['has_date'],
        data['eeat']['has_author_bio'],
        data['eeat']['has_sources']
    ]) * 2.5
    breakdown['eeat'] = {'score': eeat_score, 'max': 10}
    
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
    """Calculate scores for different AI engines"""
    base_breakdown = calculate_score_breakdown(data)
    
    engines = {
        'ChatGPT': {
            'weights': {
                'schema': 1.2,
                'questions': 1.1,
                'snippet': 1.0,
                'structure': 1.3,
                'eeat': 0.9,
                'entities': 1.0
            },
            'focus': 'Prioritizes conversational structure and clear formatting'
        },
        'Claude': {
            'weights': {
                'schema': 1.0,
                'questions': 1.2,
                'snippet': 1.0,
                'structure': 1.4,
                'eeat': 1.3,
                'entities': 1.1
            },
            'focus': 'Emphasizes content quality, trustworthiness, and natural language'
        },
        'Gemini': {
            'weights': {
                'schema': 1.3,
                'questions': 1.0,
                'snippet': 1.2,
                'structure': 1.0,
                'eeat': 1.0,
                'entities': 1.2
            },
            'focus': 'Strong preference for structured data and entities'
        },
        'Perplexity': {
            'weights': {
                'schema': 1.1,
                'questions': 1.3,
                'snippet': 1.2,
                'structure': 1.0,
                'eeat': 1.2,
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
    
    priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    recommendations.sort(key=lambda x: priority_order[x['priority']])
    
    return recommendations

# Main App
st.markdown('<p class="main-header">🎯 AEO On-Page Auditor</p>', unsafe_allow_html=True)
st.markdown("**Analyze your webpage for Answer Engine Optimization (AEO)** - optimize for AI search engines, featured snippets, and voice search.")

# Input
url = st.text_input("Enter URL to Analyze", placeholder="https://example.com/article")

if st.button("🔍 Analyze", type="primary", use_container_width=True):
    if not url:
        st.error("Please enter a URL")
    else:
        with st.spinner("Analyzing webpage..."):
            try:
                # Fetch and analyze
                html = fetch_page(url)
                soup = BeautifulSoup(html, 'html.parser')
                
                schema_data = analyze_schema(soup)
                question_data = analyze_questions(soup)
                snippet_data = analyze_snippet_optimization(soup)
                structure_data = analyze_structure(soup)
                entity_data = analyze_entities(soup)
                eeat_data = analyze_eeat(soup, url)
                
                result = {
                    'schema': schema_data,
                    'questions': question_data,
                    'snippet': snippet_data,
                    'structure': structure_data,
                    'entities': entity_data,
                    'eeat': eeat_data
                }
                
                score_breakdown = calculate_score_breakdown(result)
                engine_scores = calculate_engine_scores(result)
                recommendations = generate_prioritized_recommendations(result)
                
                # Display Results
                st.success(f"✅ Analysis complete for: {url}")
                
                # Overall Score
                aeo_score = score_breakdown['total']
                score_class = "score-high" if aeo_score >= 80 else "score-medium" if aeo_score >= 60 else "score-low"
                
                st.markdown(f"""
                <div class="score-card {score_class}">
                    <h2>Overall AEO Score</h2>
                    <h1 style="font-size: 4rem; margin: 1rem 0;">{aeo_score}</h1>
                    <p>out of 100</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Quick Checks
                st.subheader("✓ Quick Checks")
                col1, col2, col3 = st.columns(3)
                
                checks = {
                    'FAQ Schema': schema_data['faq_present'],
                    'HowTo Schema': schema_data['howto_present'],
                    'Question Headings': question_data['question_headings'] >= 3,
                    'Snippet Ready': snippet_data['snippet_score'] >= 50,
                    'Has TL;DR': structure_data['has_tldr'],
                    'Good Readability': structure_data['flesch_reading_ease'] >= 60,
                    'Author Info': eeat_data['has_author_meta']
                }
                
                for i, (check, passed) in enumerate(checks.items()):
                    col = [col1, col2, col3][i % 3]
                    icon = "✅" if passed else "❌"
                    col.metric(check, icon)
                
                # Engine Scores
                st.subheader("🤖 Score by Answer Engine")
                st.markdown("Different AI engines prioritize different content factors.")
                
                cols = st.columns(2)
                for i, (engine, data) in enumerate(engine_scores.items()):
                    with cols[i % 2]:
                        score = data['score']
                        st.metric(engine, f"{score}/100")
                        st.caption(data['focus'])
                        st.progress(score / 100)
                
                # Score Breakdown
                st.subheader("📊 Score Breakdown by Component")
                
                component_names = {
                    'schema': 'Schema Markup',
                    'questions': 'Question Content',
                    'snippet': 'Snippet Optimization',
                    'structure': 'Content Structure',
                    'eeat': 'E-E-A-T Signals',
                    'entities': 'Entity Recognition'
                }
                
                for component, values in score_breakdown['breakdown'].items():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{component_names[component]}**")
                        st.progress(values['score'] / values['max'])
                    with col2:
                        st.write(f"{values['score']}/{values['max']}")
                
                # Prioritized Recommendations
                st.subheader("⚠️ Prioritized Recommendations")
                
                for rec in recommendations:
                    priority_class = f"priority-{rec['priority'].lower()}"
                    st.markdown(f"""
                    <div class="{priority_class}">
                        <strong style="color: #1F2937;">🔴 {rec['priority']}</strong> - {rec['category']} | Effort: {rec['effort']}<br/>
                        <strong style="font-size: 1.1rem; color: #111827;">{rec['action']}</strong><br/>
                        <em style="color: #4B5563;">{rec['impact']}</em>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Detailed Metrics
                st.subheader("📋 Detailed Metrics")
                
                tab1, tab2, tab3, tab4 = st.tabs(["Schema", "Snippet", "Structure", "E-E-A-T"])
                
                with tab1:
                    st.write(f"**FAQ Schema:** {'Yes (' + str(schema_data['faq_count']) + ' items)' if schema_data['faq_present'] else 'No'}")
                    st.write(f"**HowTo Schema:** {'Yes (' + str(schema_data['howto_count']) + ' steps)' if schema_data['howto_present'] else 'No'}")
                    st.write(f"**Article Schema:** {'Yes' if schema_data['article_present'] else 'No'}")
                
                with tab2:
                    st.write(f"**First Paragraph:** {snippet_data['first_para_words']} words")
                    st.write(f"**Lists:** {snippet_data['lists']}")
                    st.write(f"**Tables:** {snippet_data['tables']}")
                    st.write(f"**Snippet Score:** {snippet_data['snippet_score']}/100")
                
                with tab3:
                    st.write(f"**Word Count:** {structure_data['word_count']}")
                    st.write(f"**Question Headings:** {question_data['question_headings']}/{question_data['total_headings']}")
                    st.write(f"**Readability Score:** {structure_data['flesch_reading_ease']}")
                    st.write(f"**Has TL;DR:** {'Yes' if structure_data['has_tldr'] else 'No'}")
                    
                    if question_data['question_heading_examples']:
                        st.write("**Question Headings Found:**")
                        for q in question_data['question_heading_examples']:
                            st.write(f"- {q}")
                
                with tab4:
                    st.write(f"**Author Meta:** {'Yes' if eeat_data['has_author_meta'] else 'No'}")
                    st.write(f"**Publication Date:** {'Yes' if eeat_data['has_date'] else 'No'}")
                    st.write(f"**Author Bio:** {'Yes' if eeat_data['has_author_bio'] else 'No'}")
                    st.write(f"**Sources/References:** {'Yes' if eeat_data['has_sources'] else 'No'}")
                
            except Exception as e:
                st.error(f"Error analyzing URL: {str(e)}")
                st.info("Make sure the URL is accessible and returns valid HTML content.")

# Footer
st.markdown("---")
st.markdown("**AEO On-Page Auditor** | Optimize your content for AI search engines like ChatGPT, Claude, Gemini, and Perplexity")

