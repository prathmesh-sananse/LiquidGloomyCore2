from collections import defaultdict
from flask import Flask, render_template, request, flash, redirect
from neo4j import GraphDatabase, basic_auth

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'


# Establish connection to Neo4j database
driver = GraphDatabase.driver(uri='bolt://54.161.177.77:7687', auth=basic_auth("neo4j","power-crowds-flowers"))
session = driver.session()

@app.route('/', methods=['GET', 'POST'])
def index():
    page = request.args.get('page', default=1, type=int)
    page_size = 8
    if request.method == 'POST':
        search_term = request.form.get('search_term')
        blogs = search_blogs(search_term, page, page_size)
        return render_template('index.html', blogs=blogs, page=page, page_size=page_size)
    else:
        blogs = fetch_blogs(page, page_size)
        return render_template('index.html', blogs=blogs, page=page, page_size=page_size)

@app.route('/add_blog', methods=['GET', 'POST'])
def add_blog():
    if request.method == 'POST':
        blog_name = request.form['blog_name']
        preview = request.form['preview']
        url = request.form['url']
        owner = request.form['owner']
        category = request.form['category']
        publish_date = request.form['publish_date']
        expire_date = request.form['expire_date']
        relevance = request.form['relevance']
        target_audience = request.form['target_audience']
        region = request.form['region']

        # Custom Cypher query to create blog node and relationships
        query = """
        MERGE (b:Blog {name: $blog_name, preview: $preview, url: $url, owner: $owner, 
                      publish_date: $publish_date, expire_date: $expire_date})
        MERGE (c:Category {name: $category})
        MERGE (r:Relevance {name: $relevance})
        MERGE (t:TargetAudience {name: $target_audience})
        MERGE (re:Region {name: $region})
        MERGE (b)-[:BELONGS_TO]->(c)
        MERGE (b)-[:HAS_RELEVANCE]->(r)
        MERGE (b)-[:TARGETS]->(t)
        MERGE (b)-[:BELONGS_TO_REGION]->(re)
        """
        session.run(query, blog_name=blog_name, preview=preview, url=url, owner=owner,
                    category=category, publish_date=publish_date, expire_date=expire_date,
                    relevance=relevance, target_audience=target_audience, region=region)

        flash('Blog added successfully!')
        return redirect('/')
    else:
        return render_template('add_blog.html')

def fetch_blogs(page, page_size):
    query = """
    MATCH (b:Blog)-[:BELONGS_TO]->(category:Category)
    MATCH (b)-[:BELONGS_TO_REGION]->(region:Region)
    MATCH (b)-[:HAS_RELEVANCE]->(relevance:Relevance)
    MATCH (b)-[:TARGETS]->(target:TargetAudience)
    RETURN b.name AS name, b.url AS url, category.name AS category, 
           b.publish_date AS publish_date, b.expire_date AS expire_date, b.preview AS preview, b.owner AS owner, 
           region.name AS region, relevance.name AS relevance, 
           collect(target.name) AS target_audience
    ORDER BY b.name
    SKIP $skip
    LIMIT $limit
    """
    data = session.run(query, skip=(page - 1) * page_size, limit=page_size)
    return process_data(data)

def search_blogs(search_term, page, page_size):
    query = """
    MATCH (b:Blog)-[:BELONGS_TO]->(category:Category)
    MATCH (b)-[:BELONGS_TO_REGION]->(region:Region)
    MATCH (b)-[:HAS_RELEVANCE]->(relevance:Relevance)
    MATCH (b)-[:TARGETS]->(target:TargetAudience)
    WHERE b.name = $search_term OR category.name = $search_term OR region.name = $search_term OR relevance.name = $search_term OR target.name = $search_term
    RETURN b.name AS name, b.url AS url, category.name AS category, 
           b.publish_date AS publish_date, b.expire_date AS expire_date, b.preview AS preview, b.owner AS owner, 
           region.name AS region, relevance.name AS relevance, 
           collect(target.name) AS target_audience
    ORDER BY b.name
    SKIP $skip
    LIMIT $limit
    """
    data = session.run(query, search_term=search_term, skip=(page - 1) * page_size, limit=page_size)
    return process_data(data)

def process_data(data):
    blogs = []
    for record in data:
        blog = {
            "name": record["name"],
            "url": record["url"],
            "publish_date": record["publish_date"],
            "expire_date": record["expire_date"],
            "preview": record["preview"],
            "owner": record["owner"],
            "category": record["category"],
            "region": record["region"],
            "relevance": record["relevance"], 
            "target_audience": record["target_audience"]
        }

        if isinstance(blog["relevance"], list) and len(blog["relevance"]) > 1:
            blog["relevance"] = ", ".join(blog["relevance"])  

        if isinstance(blog["target_audience"], list) and len(blog["target_audience"]) > 1:
            blog["target_audience"] = ", ".join(blog["target_audience"])  

        blogs.append(blog)

    sorted_blogs = sorted(blogs, key=lambda x: x["name"])
    return sorted_blogs

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.run(host='0.0.0.0', port=80, debug=True)
