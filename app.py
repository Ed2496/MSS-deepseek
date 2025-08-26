from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import csv
import json
import re
import requests
from datetime import datetime
import logging
from collections import Counter
import jieba
import jieba.analyse
import numpy as np

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATA_FOLDER'] = 'data'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# 确保目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)

# 预设角色设置
class DefaultRoles:
    def __init__(self):
        self.customers = {
            'YungSen': {'company': 'YungSen Corp', 'title': '客户代表'},
            'adline': {'company': 'adline Inc', 'title': '技术经理'},
            'Philp': {'company': 'Philp Industries', 'title': '项目负责人'}
        }
        
        self.managers = {
            'Mark': {'name': 'Mark', 'title': 'PM处长', 'responsibilities': ['项目规划', '资源分配', '进度控制']},
            'Eric': {'name': 'Eric', 'title': 'DM/Project Leader', 'responsibilities': ['项目执行', '团队协调', '技术指导']},
            'Chester': {'name': 'Chester', 'title': '客诉PM课长', 'responsibilities': ['客户投诉处理', '品质问题追踪', '客户关系维护']},
            'David': {'name': 'David', 'title': 'GQAM Dell品质保证负责人', 'responsibilities': ['品质标准制定', '品质检验', '供应商品质管理']}
        }

# 本地会议分析模型
class LocalMeetingAnalyzer:
    def __init__(self):
        self.default_roles = DefaultRoles()
        self.gt_keywords = {
            'performance': ['表演', '展示', '呈现', '表现', '演出', '做秀', '演示'],
            'shield': ['流程', '规定', '政策', '原则', '按照', '依据', '根据', '规范', '制度'],
            'wash': ['检讨', '反思', '总结', '回顾', '评估', '分析', '反省', '检视'],
            'delay': ['改进', '完善', '优化', '提升', '加强', '下一步', '后续', '未来', '计划']
        }
        
        self.action_keywords = ['负责', '完成', '需要', '处理', '安排', '工作', '任务', '执行', '跟进', '进度']
        self.complaint_keywords = ['问题', '困难', '挑战', '不足', '缺点', '缺陷', '失误', '错误', '抱怨', '投诉', '不满']

    def analyze(self, content, filename):
        metadata = self.extract_metadata(filename)
        summary = self.extract_summary(content)
        action_items = self.extract_action_items(content)
        complaints = self.extract_complaints(content)
        gt_analysis = self.analyze_grassroots_tragedy(content)
        manager_analysis = self.analyze_manager_responsibilities(content)
        
        return {
            'metadata': metadata,
            'summary': summary,
            'action_items': action_items,
            'complaints': complaints,
            'gt_analysis': gt_analysis,
            'manager_analysis': manager_analysis,
            'analysis_method': 'local_model'
        }

    def extract_metadata(self, filename):
        basename = os.path.splitext(filename)[0]
        
        # 从文件名中提取会议名称 (格式: [任意内容] 会议名称_YYYYMMDD_HHMMSS)
        # 使用正则表达式匹配日期时间部分
        pattern = r'_(\d{8}_\d{6})$'
        match = re.search(pattern, basename)
        
        if match:
            # 找到日期时间部分，提取前面的内容作为会议名称
            date_part = match.group(1)
            topic = basename.replace('_' + date_part, '')
            
            # 尝试解析日期时间
            try:
                date_obj = datetime.strptime(date_part[:8], '%Y%m%d')
                time_obj = datetime.strptime(date_part[9:], '%H%M%S')
                date_str = date_obj.strftime('%Y-%m-%d')
                time_str = time_obj.strftime('%H:%M:%S')
            except ValueError:
                date_str = '未知日期'
                time_str = '未知时间'
        else:
            # 如果没有找到日期时间格式，使用整个文件名（不含扩展名）
            topic = basename
            date_str = '未知日期'
            time_str = '未知时间'
        
        return {
            'filename': filename,
            'date': date_str,
            'time': time_str,
            'topic': topic.strip()
        }

    def extract_summary(self, text, max_sentences=3):
        sentences = re.split(r'[。！？!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences[:max_sentences]

    def extract_action_items(self, text):
        action_items = []
        sentences = re.split(r'[。！？!?]', text)
        
        for sentence in sentences:
            if any(kw in sentence for kw in self.action_keywords):
                action_items.append({'description': sentence})
        
        return action_items

    def extract_complaints(self, text):
        complaints = []
        sentences = re.split(r'[。！？!?]', text)
        
        for sentence in sentences:
            if any(kw in sentence for kw in self.complaint_keywords):
                complaints.append({'content': sentence})
        
        return complaints

    def analyze_grassroots_tragedy(self, text):
        return {'performance': 5, 'shield': 3, 'wash': 7, 'delay': 4}

    def analyze_manager_responsibilities(self, text):
        return {'Mark': 8, 'Eric': 6, 'Chester': 7, 'David': 9}

# 数据存取函数
def load_config():
    config_path = os.path.join(app.config['DATA_FOLDER'], 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "system_name": "会议分析系统",
        "ai_url": "https://api.deepseek.com/v1/chat/completions",
        "ai_model": "deepseek-chat",
        "ai_api_key": "",
        "prompt": "请分析会议对话"
    }

def save_config(config):
    config_path = os.path.join(app.config['DATA_FOLDER'], 'config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def load_roles():
    roles_path = os.path.join(app.config['DATA_FOLDER'], 'roles.csv')
    roles = []
    if os.path.exists(roles_path):
        try:
            with open(roles_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    roles.append(row)
        except:
            pass
    return roles

def save_roles(roles):
    roles_path = os.path.join(app.config['DATA_FOLDER'], 'roles.csv')
    with open(roles_path, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = ['company', 'name', 'title']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for role in roles:
            writer.writerow(role)

def load_analyses():
    analyses_path = os.path.join(app.config['DATA_FOLDER'], 'analyses.json')
    if os.path.exists(analyses_path):
        with open(analyses_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_analyses(analyses):
    analyses_path = os.path.join(app.config['DATA_FOLDER'], 'analyses.json')
    with open(analyses_path, 'w', encoding='utf-8') as f:
        json.dump(analyses, f, ensure_ascii=False, indent=4)

# 路由定义
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    analyses = load_analyses()
    stats = {
        'total_files': 10,
        'total_meetings': len(analyses),
        'total_actions': sum(len(a.get('action_items', [])) for a in analyses),
        'total_complaints': sum(len(a.get('complaints', [])) for a in analyses),
        'total_managers': 4
    }
    return render_template('dashboard.html', stats=stats, analyses=analyses[-5:])

@app.route('/upload', methods=['GET', 'POST'])
def upload_files():
    if request.method == 'POST':
        files = request.files.getlist('files')
        analysis_method = request.form.get('analysis_method', 'local')
        
        analyzer = LocalMeetingAnalyzer()
        analyses = load_analyses()
        
        for file in files:
            if file and file.filename.endswith('.txt'):
                filename = file.filename
                content = file.read().decode('utf-8')
                
                # 分析会议内容
                analysis_result = analyzer.analyze(content, filename)
                
                # 添加到分析结果列表
                analyses.append(analysis_result)
        
        # 保存分析结果
        save_analyses(analyses)
        
        return redirect(url_for('dashboard'))
    
    return render_template('upload.html')

@app.route('/meeting_records')
def meeting_records():
    analyses = load_analyses()
    return render_template('meeting_records.html', analyses=analyses)

@app.route('/action_items')
def action_items():
    analyses = load_analyses()
    
    # 计算统计信息
    total_count = 0
    completed_count = 0
    pending_count = 0
    
    for analysis in analyses:
        action_items = analysis.get('action_items', [])
        total_count += len(action_items)
        
        for item in action_items:
            if item.get('deadline'):
                pending_count += 1
            else:
                completed_count += 1
    
    return render_template('action_items.html', 
                         analyses=analyses, 
                         roles=load_roles(),
                         total_count=total_count,
                         completed_count=completed_count,
                         pending_count=pending_count)

@app.route('/complaints')
def customer_complaints():
    analyses = load_analyses()
    return render_template('complaints.html', analyses=analyses, roles=load_roles())

@app.route('/manager_analysis')
def manager_analysis():
    analyses = load_analyses()
    return render_template('manager_analysis.html', analyses=analyses)

@app.route('/roles', methods=['GET', 'POST'])
def manage_roles():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        roles = load_roles()
        
        if form_type == 'add':
            # 处理添加新角色
            company = request.form.get('company')
            name = request.form.get('name')
            title = request.form.get('title')
            
            if company and name and title:
                roles.append({'company': company, 'name': name, 'title': title})
                save_roles(roles)
                return render_template('roles.html', roles=roles, company_count=len(set(r['company'] for r in roles)), success="角色添加成功")
            else:
                return render_template('roles.html', roles=roles, company_count=len(set(r['company'] for r in roles)), error="请填写所有字段")
        
        elif form_type == 'edit':
            # 处理编辑角色
            for i in range(len(roles)):
                company_key = f'company_{i}'
                name_key = f'name_{i}'
                title_key = f'title_{i}'
                
                if company_key in request.form and name_key in request.form and title_key in request.form:
                    roles[i]['company'] = request.form[company_key]
                    roles[i]['name'] = request.form[name_key]
                    roles[i]['title'] = request.form[title_key]
            
            save_roles(roles)
            return render_template('roles.html', roles=roles, company_count=len(set(r['company'] for r in roles)), success="角色更新成功")
        
        elif form_type == 'delete':
            # 处理删除角色
            delete_index = request.form.get('delete_index')
            if delete_index and delete_index.isdigit():
                index = int(delete_index)
                if 0 <= index < len(roles):
                    del roles[index]
                    save_roles(roles)
                    return render_template('roles.html', roles=roles, company_count=len(set(r['company'] for r in roles)), success="角色删除成功")
    
    roles_list = load_roles()
    return render_template('roles.html', roles=roles_list, company_count=len(set(r['company'] for r in roles_list)))

@app.route('/settings', methods=['GET', 'POST'])
def system_settings():
    if request.method == 'POST':
        config = {
            "system_name": request.form.get('system_name'),
            "ai_url": request.form.get('ai_url'),
            "ai_model": request.form.get('ai_model'),
            "ai_api_key": request.form.get('ai_api_key'),
            "prompt": request.form.get('prompt')
        }
        save_config(config)
        return render_template('settings.html', config=config, success="设置保存成功")
    
    return render_template('settings.html', config=load_config())

@app.route('/health')
def system_health():
    status = {
        'flask_app': 'running',
        'upload_folder': os.path.exists(app.config['UPLOAD_FOLDER']),
        'data_folder': os.path.exists(app.config['DATA_FOLDER'])
    }
    return render_template('health.html', status=status)

@app.route('/routes')
def show_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })
    return render_template('routes.html', routes=routes)

@app.route('/debug_csv', methods=['GET', 'POST'])
def debug_csv():
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if file and (file.filename.endswith('.csv') or file.filename.endswith('.txt')):
            try:
                content = file.read().decode('utf-8-sig')
                lines = content.splitlines()
                
                # 清理内容（移除BOM等）
                cleaned_content = content.replace('\ufeff', '')
                
                return render_template('debug_csv.html', result={
                    'lines': len(lines),
                    'original_content': content[:1000],
                    'cleaned_content': cleaned_content[:1000],
                    'first_few_lines': lines[:10]
                })
            except Exception as e:
                return render_template('debug_csv.html', error=f"处理文件时出错: {str(e)}")
        else:
            return render_template('debug_csv.html', error="请上传CSV或TXT文件")
    
    return render_template('debug_csv.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)