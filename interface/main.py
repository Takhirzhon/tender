import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
import base64

# Set page config
st.set_page_config(
    page_title="ProZorro Tender Analyzer",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Ukrainian styling
st.markdown("""
<style>
    .stApp {
        background-color: #f0f2f6;
    }
    .st-emotion-cache-1v0mbdj {
        border: 2px solid #005bbb !important;
        border-radius: 10px;
    }
    .stButton>button {
        background-color: #005bbb !important;
        color: white !important;
        border-radius: 5px;
        font-weight: bold;
    }
    .stSelectbox>div>div>select {
        border-color: #005bbb !important;
    }
    .stFileUploader>div>div>div>div>div>div>div>div {
        border-color: #005bbb !important;
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #005bbb !important;
    }
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #ffd500;
        color: #005bbb;
        text-align: center;
        padding: 10px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Ukrainian translations
UKR_TRANSLATIONS = {
    "app_title": "Аналізатор Тендерів ProZorro",
    "upload_header": "Завантаження даних тендеру",
    "upload_description": "Завантажте JSON-файл тендеру з системи ProZorro",
    "sample_tender": "Завантажити зразок тендеру",
    "analyze_btn": "Аналізувати Тендер",
    "tender_details": "Деталі Тендеру",
    "tender_id": "ID тендеру",
    "tender_title": "Назва тендеру",
    "description": "Опис",
    "status": "Статус",
    "procuring_entity": "Замовник",
    "value": "Вартість",
    "currency": "грн",
    "tender_period": "Період проведення тендеру",
    "enquiry_period": "Період запитів",
    "items": "Предмети закупівлі",
    "item_description": "Опис",
    "quantity": "Кількість",
    "unit": "Одиниця виміру",
    "classification": "Класифікація",
    "delivery_address": "Адреса доставки",
    "delivery_date": "Строки поставки",
    "raw_data": "Необроблені дані",
    "download_report": "Завантажити звіт",
    "footer_text": "Розроблено для підтримки прозорих закупівель в Україні | Версія 1.0",
    "no_file": "Будь ласка, завантажте файл тендеру",
    "file_error": "Помилка при обробці файлу. Перевірте формат.",
    "tender_id_missing": "ID тендеру відсутній",
    "title_missing": "Назва тендеру відсутня",
    "description_missing": "Опис відсутній",
    "statuses": {
        "active.enquiries": "Прийом запитань",
        "active.tendering": "Прийом пропозицій",
        "active.auction": "Аукціон",
        "active.qualification": "Кваліфікація",
        "active.awarded": "Оголошено переможця",
        "complete": "Завершено",
        "cancelled": "Скасовано",
        "unsuccessful": "Не відбувся"
    }
}

# Sample tender data
SAMPLE_TENDER = {
    "id": "UA-2025-07-123456",
    "title": "Реконструкція школи у Києві",
    "description": "Повна реконструкція будівлі школи з заміною комунікацій та оснащенням сучасним обладнанням",
    "status": "active.tendering",
    "procuringEntity": {
        "name": "Київська міська рада",
        "address": {
            "streetAddress": "Хрещатик, 36",
            "locality": "Київ",
            "region": "м.Київ"
        }
    },
    "value": {
        "amount": 5200000,
        "currency": "UAH"
    },
    "tenderPeriod": {
        "startDate": "2025-07-01T10:00:00+03:00",
        "endDate": "2025-08-15T17:00:00+03:00"
    },
    "enquiryPeriod": {
        "startDate": "2025-07-01T10:00:00+03:00",
        "endDate": "2025-07-30T17:00:00+03:00"
    },
    "items": [
        {
            "description": "Бетонні роботи",
            "quantity": 120,
            "unit": {
                "name": "куб.м"
            },
            "classification": {
                "scheme": "ДК021",
                "id": "45210000-2",
                "description": "Будівельні роботи"
            },
            "deliveryAddress": {
                "streetAddress": "вул. Шкільна, 5",
                "locality": "Київ",
                "region": "м.Київ"
            },
            "deliveryDate": {
                "startDate": "2025-09-01",
                "endDate": "2026-05-31"
            }
        },
        {
            "description": "Електромонтажні роботи",
            "quantity": 350,
            "unit": {
                "name": "кв.м"
            },
            "classification": {
                "scheme": "ДК021",
                "id": "45310000-1",
                "description": "Електромонтажні роботи"
            },
            "deliveryAddress": {
                "streetAddress": "вул. Шкільна, 5",
                "locality": "Київ",
                "region": "м.Київ"
            },
            "deliveryDate": {
                "startDate": "2025-09-01",
                "endDate": "2026-05-31"
            }
        }
    ]
}

def format_date(date_str):
    """Format ISO date to Ukrainian format"""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return date_str

def parse_tender_data(tender_json):
    """Parse and structure tender data"""
    try:
        data = {
            "id": tender_json.get("id", UKR_TRANSLATIONS["tender_id_missing"]),
            "title": tender_json.get("title", UKR_TRANSLATIONS["title_missing"]),
            "description": tender_json.get("description", UKR_TRANSLATIONS["description_missing"]),
            "status": UKR_TRANSLATIONS["statuses"].get(
                tender_json.get("status", ""), 
                tender_json.get("status", "Невідомий статус")
            ),
            "procuring_entity": tender_json.get("procuringEntity", {}).get("name", "Невідомо"),
            "value": tender_json.get("value", {}).get("amount", 0),
            "currency": tender_json.get("value", {}).get("currency", "UAH"),
            "tender_start": format_date(tender_json.get("tenderPeriod", {}).get("startDate", "")),
            "tender_end": format_date(tender_json.get("tenderPeriod", {}).get("endDate", "")),
            "enquiry_start": format_date(tender_json.get("enquiryPeriod", {}).get("startDate", "")),
            "enquiry_end": format_date(tender_json.get("enquiryPeriod", {}).get("endDate", "")),
            "items": []
        }
        
        # Process items
        for item in tender_json.get("items", []):
            data["items"].append({
                "description": item.get("description", "Без опису"),
                "quantity": item.get("quantity", 1),
                "unit": item.get("unit", {}).get("name", "шт."),
                "classification": item.get("classification", {}).get("description", "Не класифіковано"),
                "delivery_address": item.get("deliveryAddress", {}).get("streetAddress", "Не вказано"),
                "delivery_date_start": format_date(item.get("deliveryDate", {}).get("startDate", "")),
                "delivery_date_end": format_date(item.get("deliveryDate", {}).get("endDate", ""))
            })
            
        return data
    except Exception as e:
        st.error(f"{UKR_TRANSLATIONS['file_error']}: {str(e)}")
        return None

def create_download_link(data, filename):
    """Generate download link for files"""
    if filename.endswith('.json'):
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        b64 = base64.b64encode(json_str.encode('utf-8')).decode()
    elif filename.endswith('.csv'):
        if isinstance(data, list):
            df = pd.DataFrame(data)
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            b64 = base64.b64encode(csv.encode('utf-8-sig')).decode()
        else:
            return None
    else:
        return None
        
    return f'<a href="data:file/{filename.split(".")[-1]};base64,{b64}" download="{filename}">Завантажити {filename}</a>'

# Main app
st.title(f"📑 {UKR_TRANSLATIONS['app_title']}")
st.markdown("---")

# Sidebar for file upload
with st.sidebar:
    st.header(f"📤 {UKR_TRANSLATIONS['upload_header']}")
    st.caption(UKR_TRANSLATIONS["upload_description"])
    
    uploaded_file = st.file_uploader(
        label="Оберіть файл тендеру (JSON)",
        type=["json"],
        accept_multiple_files=False
    )
    
    if st.button(UKR_TRANSLATIONS["sample_tender"]):
        uploaded_file = None
        tender_data = SAMPLE_TENDER
        st.session_state.tender_data = tender_data
        st.success("Зразок тендеру завантажено!")
    
    st.markdown("---")
    st.caption("Розроблено з використанням:")
    st.image("https://prozorro.gov.ua/static/img/logo.svg", width=150)
    st.caption("Дані з офіційного API ProZorro")

# Main content
if uploaded_file is not None:
    try:
        tender_data = json.load(uploaded_file)
        st.session_state.tender_data = tender_data
    except:
        st.error(UKR_TRANSLATIONS["file_error"])

if 'tender_data' in st.session_state:
    tender = parse_tender_data(st.session_state.tender_data)
    
    if tender:
        st.header(f"ℹ️ {UKR_TRANSLATIONS['tender_details']}")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Основна інформація")
            st.info(f"**{UKR_TRANSLATIONS['tender_id']}:** {tender['id']}")
            st.info(f"**{UKR_TRANSLATIONS['tender_title']}:** {tender['title']}")
            st.info(f"**{UKR_TRANSLATIONS['status']}:** {tender['status']}")
            st.info(f"**{UKR_TRANSLATIONS['procuring_entity']}:** {tender['procuring_entity']}")
            st.info(f"**{UKR_TRANSLATIONS['value']}:** {tender['value']:,} {tender['currency']}")
            
        with col2:
            st.subheader("Дати проведення")
            st.info(f"**Початок тендеру:** {tender['tender_start']}")
            st.info(f"**Закінчення тендеру:** {tender['tender_end']}")
            st.info(f"**Період запитів (початок):** {tender['enquiry_start']}")
            st.info(f"**Період запитів (закінчення):** {tender['enquiry_end']}")
        
        st.subheader(f"📦 {UKR_TRANSLATIONS['items']}")
        
        if tender['items']:
            items_df = pd.DataFrame(tender['items'])
            st.dataframe(items_df, use_container_width=True)
        else:
            st.warning("Предмети закупівлі не знайдені")
        
        st.subheader("📝 Додаткові опції")
        tab1, tab2 = st.tabs(["Необроблені дані", "Завантажити звіт"])
        
        with tab1:
            st.subheader(UKR_TRANSLATIONS["raw_data"])
            st.json(st.session_state.tender_data, expanded=False)
            
        with tab2:
            st.subheader(UKR_TRANSLATIONS["download_report"])
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Зберегти у форматі JSON"):
                    download_link = create_download_link(
                        st.session_state.tender_data, 
                        f"tender_{tender['id']}.json"
                    )
                    st.markdown(download_link, unsafe_allow_html=True)
                    
            with col2:
                if st.button("Зберегти у форматі CSV"):
                    if tender['items']:
                        download_link = create_download_link(
                            tender['items'], 
                            f"tender_items_{tender['id']}.csv"
                        )
                        if download_link:
                            st.markdown(download_link, unsafe_allow_html=True)
                        else:
                            st.error("Помилка при створенні CSV-файлу")
                    else:
                        st.warning("Немає даних для експорту у форматі CSV")

# Footer
st.markdown("---")
st.markdown(f'<div class="footer">{UKR_TRANSLATIONS["footer_text"]}</div>', unsafe_allow_html=True)