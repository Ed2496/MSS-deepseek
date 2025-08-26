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

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATA_FOLDER'] = 'data'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# 確保目錄存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)

# 預設角色設定
class DefaultRoles:
    def __init__(self):
        self.customers = {
            'YungSen': {'company': 'YungSen Corp', 'title': '客戶代表'},
            'adline': {'company': 'adline Inc', 'title': '技術經理'},
            'Philp': {'company': 'Philp Industries', 'title': '專案負責人'}
        }
        
        self.managers = {
            'Mark': {'name': 'Mark', 'title': 'PM處長', 'responsibilities': ['專案規劃', '資源分配', '進度控制']},
            'Eric': {'name': 'Eric', 'title': 'DM/Project Leader', 'responsibilities': ['專案執行', '團隊協調', '技術指導']},
            'Chester': {'name': 'Chester', 'title': '客訴PM課長', 'responsibilities': ['客戶投訴處理', '品質問題追蹤', '客戶關係維護']},
            'David': {'name': 'David', 'title': 'GQAM Dell品質保證負責人', 'responsibilities': ['品質標準制定', '品質檢驗', '供應商品質管理']}
        }

# 本地會議分析模型
class LocalMeetingAnalyzer:
    def __init__(self):
        self.default_roles = DefaultRoles()
        self.gt_keywords = {
            'performance': ['表演', '展示', '呈現', '表現', '演出', '做秀', '演示'],
            'shield': ['流程', '規定', '政策', '原則', '按照', '依據', '根據', '規範', '制度'],
            'wash': ['檢討', '反思', '總結', '回顧', '評估', '分析', '反省', '檢視'],
            'delay': ['改進', '完善', '優化', '提升', '加強', '下一步', '後續', '未來', '計畫']
        }
        
        self.action_keywords = ['負責', '完成', '需要', '處理', '安排', '工作', '任務', '執行', '跟進', '進度']
        self.complaint_keywords = ['問題', '困難', '挑戰', '不足', '缺點', '缺陷', '失誤', '錯誤', '抱怨', '投訴', '不滿']

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
        parts = re.split(r'[_\-\s]+', basename)
        
        date_str, time_str, topic = None, None, []
        for part in parts:
            if re.match(r'^\d{8}$', part):
                date_str = part
            elif re.match(r'^\d{6}$', part):
                time_str = part
            else:
                topic.append(part)
        
        return {
            'date': date_str or '未知日期',
            'time': time_str or '未知時間',
            'topic': ' '.join(topic) or '未命名會議'
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

# 數據存取函數
def load_config():
    config_path = os.path.join(app.config['DATA_FOLDER'], 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "system_name": "會議分析系統",
        "ai_url": "https://api.deepseek.com/v1/chat/completions",
        "ai_model": "deepseek-chat",
        "ai_api_key": "",
        "prompt": "請分析會議對話"
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

# 路由定義
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
        return redirect(url_for('dashboard'))
    return render_template('upload.html')

@app.route('/meeting_records')
def meeting_records():
    return render_template('meeting_records.html', analyses=load_analyses())

@app.route('/action_items')
def action_items():
    return render_template('action_items.html', analyses=load_analyses(), roles=load_roles())

@app.route('/complaints')
def customer_complaints():
    return render_template('complaints.html', analyses=load_analyses(), roles=load_roles())

@app.route('/manager_analysis')
def manager_analysis():
    return render_template('manager_analysis.html', analyses=load_analyses())

@app.route('/roles', methods=['GET', 'POST'])
def manage_roles():
    roles_list = load_roles()
    return render_template('roles.html', roles=roles_list, company_count=len(set(r['company'] for r in roles_list)))

@app.route('/settings', methods=['GET', 'POST'])
def system_settings():
    return render_template('settings.html', config=load_config())

@app.route('/health')
def system_health():
    status = {
        'flask_app': 'running',
        'upload_folder': os.path.exists(app.config['UPLOAD_FOLDER']),
        'data_folder': os.path.exists(app.config['DATA_FOLDER'])
    }
    return render_template('health.html', status=status)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)