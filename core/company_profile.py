# company_profile.py
import json
import os
from datetime import datetime

class CompanyProfile:
    def __init__(self, profile_path="data/company_profile.json"):
        self.profile_path = profile_path
        self.profile = self.load_profile()
    
    def load_profile(self):
        if os.path.exists(self.profile_path):
            with open(self.profile_path, "r") as f:
                return json.load(f)
        return {
            "company_name": "",
            "resources": {},
            "document_vault": [],
            "historical_performance": [],
            "capabilities": [],
            "last_updated": datetime.now().isoformat()
        }
    
    def save_profile(self):
        with open(self.profile_path, "w") as f:
            json.dump(self.profile, f, indent=2)
    
    def add_document(self, doc_name, doc_type, validity, file_path, tags=None):
        new_doc = {
            "id": f"DOC-{len(self.profile['document_vault']) + 1:04d}",
            "name": doc_name,
            "type": doc_type,
            "validity": validity,
            "path": file_path,
            "tags": tags or [],
            "added_date": datetime.now().isoformat()
        }
        self.profile["document_vault"].append(new_doc)
        self.save_profile()
        return new_doc
    
    def update_resources(self, resources):
        self.profile["resources"] = resources
        self.save_profile()
    
    def add_capability(self, capability):
        if capability not in self.profile["capabilities"]:
            self.profile["capabilities"].append(capability)
            self.save_profile()
    
    def add_performance_record(self, tender_id, outcome, profit, lessons):
        record = {
            "tender_id": tender_id,
            "outcome": outcome,
            "profit": profit,
            "lessons": lessons,
            "date": datetime.now().isoformat()
        }
        self.profile["historical_performance"].append(record)
        self.save_profile()