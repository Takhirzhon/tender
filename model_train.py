import pandas as pd
import numpy as np
import re
from datetime import datetime
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class TenderIntelligence:
    def __init__(self, tender_data, company_profile):
        """
        Initialize the intelligence layer with tender data and company profile
        
        Args:
            tender_data (DataFrame): Extracted tender data from Claude
            company_profile (dict): Company capabilities and preferences
        """
        self.df = tender_data
        self.company = company_profile
        self.prepare_data()
        self.vectorizer = TfidfVectorizer(stop_words='english')
        
    def prepare_data(self):
        """Clean and preprocess tender data"""
        self.df['clean_budget'] = self.df['Budget'].apply(self.extract_budget_value)
        
        self.df['deadline_date'] = self.df['Deadline'].apply(self.parse_date)
        
        today = datetime.now().date()
        self.df['days_until_deadline'] = self.df['deadline_date'].apply(
            lambda x: (x - today).days if x and x > today else 0
        )
        
        self.df['project_category'] = self.df['Project Type'].apply(self.categorize_project)
        
    def extract_budget_value(self, budget_str):
        """Convert budget strings to numeric values"""
        if pd.isna(budget_str) or 'not specified' in str(budget_str).lower():
            return 0
        
        match = re.search(r'([£€$]?[\d,\s]+(?:\.\d+)?)', str(budget_str))
        if match:
            value_str = match.group(1).replace(',', '').replace(' ', '')
            value_str = re.sub(r'[£€$]', '', value_str)
            try:
                return float(value_str)
            except:
                return 0
        return 0
    
    def parse_date(self, date_str):
        """Convert various date formats to datetime objects"""
        if pd.isna(date_str) or 'not specified' in str(date_str).lower():
            return None
        
        patterns = [
            r'\d{1,2} (?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4}',
            r'\d{4}-\d{2}-\d{2}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2} \w{3} \d{4}',
            r'\d{1,2}\w{2} (?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, str(date_str))
            if match:
                try:
                    return datetime.strptime(match.group(), '%d %B %Y').date()
                except:
                    try:
                        return datetime.strptime(match.group(), '%Y-%m-%d').date()
                    except:
                        continue
        return None
    
    def categorize_project(self, project_type):
        """Categorize project types into standardized categories"""
        if pd.isna(project_type):
            return "Other"
        
        project_type = project_type.lower()
        
        categories = {
            'construction|renovation|building': 'Construction',
            'it|software|digital|technology': 'Technology',
            'health|medical|pharmaceutical|dental': 'Healthcare',
            'education|training|school': 'Education',
            'financial|banking|investment|insurance': 'Finance',
            'transport|logistics|vehicle': 'Transportation',
            'energy|environment|sustainability': 'Energy/Environment',
            'consulting|management|advisory': 'Consulting'
        }
        
        for pattern, category in categories.items():
            if re.search(pattern, project_type):
                return category
        
        return "Other"
    
    def calculate_scores(self):
        """Calculate multiple scores for each tender"""
        # Strategic Alignment Score
        self.df['alignment_score'] = self.df.apply(
            lambda row: self.calculate_strategic_alignment(row), axis=1
        )
        
        max_budget = self.df['clean_budget'].max() or 1  # Avoid division by zero
        self.df['financial_score'] = self.df['clean_budget'].apply(
            lambda x: min(x / max_budget, 1) * 100
        )
        
        max_days = self.df['days_until_deadline'].max() or 1
        self.df['urgency_score'] = self.df['days_until_deadline'].apply(
            lambda x: max(0, 100 - (x / max_days * 100)) if x > 0 else 100
        )
        
        self.df['risk_score'] = self.df.apply(
            lambda row: self.assess_risks(row), axis=1
        )
        
        weights = self.company.get('scoring_weights', {
            'alignment': 0.4,
            'financial': 0.3,
            'urgency': 0.2,
            'risk': 0.1
        })
        
        self.df['priority_score'] = (
            weights['alignment'] * self.df['alignment_score'] +
            weights['financial'] * self.df['financial_score'] +
            weights['urgency'] * self.df['urgency_score'] +
            weights['risk'] * (100 - self.df['risk_score'])  
        )
        
        self.df = self.df.sort_values('priority_score', ascending=False)
        
        return self.df
    
    def calculate_strategic_alignment(self, tender):
        """Calculate how well the tender aligns with company capabilities"""
        type_match = 1 if tender['project_category'] in self.company['capabilities'] else 0
        
        location_match = 0
        if 'location_preferences' in self.company:
            for loc in self.company['location_preferences']:
                if loc.lower() in str(tender['Location']).lower():
                    location_match = 1
                    break
        
        company_profile_text = " ".join([
            " ".join(self.company['capabilities']),
            " ".join(self.company.get('keywords', []))
        ])
        
        tender_text = " ".join([
            str(tender['Title']),
            str(tender['Project Type']),
            str(tender['Location'])
        ])
        
        tfidf_matrix = self.vectorizer.fit_transform([company_profile_text, tender_text])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        alignment_score = (
            0.4 * type_match * 100 +
            0.3 * location_match * 100 +
            0.3 * similarity * 100
        )
        
        return max(0, min(alignment_score, 100))
    
    def assess_risks(self, tender):
        """Assess potential risks in the tender"""
        risk_score = 0
        
        if tender['days_until_deadline'] < 14:
            risk_score += 40
        elif tender['days_until_deadline'] < 30:
            risk_score += 20
        
        if tender['clean_budget'] == 0 or "not specified" in str(tender['Budget']).lower():
            risk_score += 30
        
        compliance_terms = ['QES', 'digital signature', 'eIDAS', 'KEP', 'certified']
        tender_text = f"{tender['Title']} {tender['Project Type']}".lower()
        if any(term in tender_text for term in compliance_terms):
            if not self.company.get('qes_certified', False):
                risk_score += 50
        
        if 'framework' in tender_text or 'multi-lot' in tender_text:
            risk_score += 20
        
        return min(risk_score, 100)
    
    def generate_recommendations(self, top_n=10):
        """Generate recommendations with explanations"""
        if 'priority_score' not in self.df.columns:
            self.calculate_scores()
            
        recommendations = []
        for _, row in self.df.head(top_n).iterrows():
            reasons = []
            
            if row['alignment_score'] > 70:
                reasons.append(f"Strong alignment with {self.company['name']}'s capabilities")
            
            if row['financial_score'] > 70:
                reasons.append(f"High-value opportunity (£{row['clean_budget']:,.2f})")
            
            if row['urgency_score'] > 70:
                days = row['days_until_deadline']
                reasons.append(f"Urgent deadline ({days} days remaining)")
            
            if row['risk_score'] < 30:
                reasons.append("Low-risk opportunity")
            
            recommendations.append({
                'tender_id': row['Filename'],
                'title': row['Title'],
                'priority_score': round(row['priority_score'], 1),
                'budget': row['Budget'],
                'deadline': row['Deadline'],
                'reasons': reasons,
                'risk_level': self.get_risk_level(row['risk_score'])
            })
        
        return recommendations
    
    def get_risk_level(self, risk_score):
        """Categorize risk level"""
        if risk_score < 20:
            return "Low"
        elif risk_score < 50:
            return "Medium"
        elif risk_score < 80:
            return "High"
        else:
            return "Critical"
    
    def generate_risk_report(self):
        """Generate a comprehensive risk report"""
        risk_report = {
            'high_risk_tenders': [],
            'common_risk_factors': {},
            'compliance_check': {}
        }
        
        for _, row in self.df.iterrows():
            if row['risk_score'] > 70:
                risk_report['high_risk_tenders'].append({
                    'title': row['Title'],
                    'risk_score': row['risk_score'],
                    'primary_risk': self.get_primary_risk(row),
                    'filename': row['Filename']
                })
        
        risk_factors = {
            'deadline_risk': sum(self.df['days_until_deadline'] < 14),
            'budget_risk': sum((self.df['clean_budget'] == 0) | 
                              (self.df['Budget'].str.contains('not specified', case=False, na=False))),
            'compliance_risk': sum(self.df.apply(lambda x: 'qes' in str(x['Project Type']).lower() or 
                                   'digital signature' in str(x['Project Type']).lower(), axis=1)) &
                                 (not self.company.get('qes_certified', False))
        }
        risk_report['common_risk_factors'] = risk_factors
        
        compliance_status = {
            'qes_required': risk_factors['compliance_risk'] > 0,
            'qes_certified': self.company.get('qes_certified', False),
            'recommendation': "Obtain QES certification" if risk_factors['compliance_risk'] > 0 
                             and not self.company.get('qes_certified', False) else "Compliant"
        }
        risk_report['compliance_check'] = compliance_status
        
        return risk_report
    
    def get_primary_risk(self, tender):
        """Identify the primary risk factor for a tender"""
        risks = []
        if tender['days_until_deadline'] < 14:
            risks.append(("Deadline", 40))
        if tender['clean_budget'] == 0 or "not specified" in str(tender['Budget']).lower():
            risks.append(("Budget", 30))
        if any(term in str(tender['Project Type']).lower() 
               for term in ['qes', 'digital signature', 'eidas', 'kep', 'certified']):
            if not self.company.get('qes_certified', False):
                risks.append(("Compliance", 50))
        if 'framework' in str(tender['Project Type']).lower() or 'multi-lot' in str(tender['Project Type']).lower():
            risks.append(("Complexity", 20))
        
        if not risks:
            return "Undefined"
        
        return max(risks, key=lambda x: x[1])[0]

if __name__ == "__main__":
    tender_df = pd.read_excel("tenders/claude_extracted.xlsx")
    
    company_profile = {
        "name": "TechSolutions Ltd",
        "capabilities": ["Technology", "Consulting", "IT services"],
        "keywords": ["digital transformation", "software", "IT infrastructure"],
        "location_preferences": ["London", "United Kingdom"],
        "min_budget": 50000,  
        "qes_certified": False,
        "scoring_weights": {
            "alignment": 0.5,
            "financial": 0.3,
            "urgency": 0.1,
            "risk": 0.1
        }
    }
    
    intel = TenderIntelligence(tender_df, company_profile)
    
    scored_df = intel.calculate_scores()
    recommendations = intel.generate_recommendations(top_n=5)
    
    risk_report = intel.generate_risk_report()
    
    scored_df.to_excel("tenders/scored_tenders.xlsx", index=False)
    
    print("🚀 Top 5 Recommended Tenders:")
    for i, tender in enumerate(recommendations, 1):
        print(f"\n#{i}: {tender['title']}")
        print(f"  ⭐ Priority Score: {tender['priority_score']}/100")
        print(f"  ⚠️ Risk Level: {tender['risk_level']}")
        print(f"  💰 Budget: {tender['budget']}")
        print(f"  📅 Deadline: {tender['deadline']}")
        print("  ✅ Reasons to pursue:")
        for reason in tender['reasons']:
            print(f"     - {reason}")
    
    print("\n🔍 Risk Report Summary:")
    print(f"  High-risk tenders: {len(risk_report['high_risk_tenders'])}")
    print(f"  Tenders with budget issues: {risk_report['common_risk_factors']['budget_risk']}")
    print(f"  Urgent deadlines (<14 days): {risk_report['common_risk_factors']['deadline_risk']}")
    print(f"  QES compliance required: {risk_report['compliance_check']['qes_required']}")
    print(f"  Compliance recommendation: {risk_report['compliance_check']['recommendation']}")