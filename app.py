import streamlit as st
import sqlite3
from docx import Document
from io import BytesIO
import requests

# เชื่อมต่อกับฐานข้อมูล SQLite
conn = sqlite3.connect('dictionary.db')
cursor = conn.cursor()

# สร้างตารางถ้ายังไม่มี
cursor.execute('''CREATE TABLE IF NOT EXISTS terms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL,
                    definition TEXT NOT NULL)''')
conn.commit()

# ฟังก์ชันสำหรับการแสดงคำศัพท์ทั้งหมด
def show_terms(search_term=""):
    if search_term:
        cursor.execute("SELECT * FROM terms WHERE word LIKE ? ORDER BY word ASC", ('%' + search_term + '%',))
    else:
        cursor.execute("SELECT * FROM terms ORDER BY word ASC")
    terms = cursor.fetchall()
    return terms

# ฟังก์ชันสำหรับการเพิ่มคำศัพท์ใหม่
def add_term(word, definition):
    cursor.execute("INSERT INTO terms (word, definition) VALUES (?, ?)", (word, definition))
    conn.commit()

# ฟังก์ชันสำหรับการแก้ไขคำศัพท์
def update_term(id, word, definition):
    cursor.execute("UPDATE terms SET word = ?, definition = ? WHERE id = ?", (word, definition, id))
    conn.commit()

# ฟังก์ชันสำหรับการลบคำศัพท์
def delete_term(id):
    cursor.execute("DELETE FROM terms WHERE id = ?", (id,))
    conn.commit()

# ฟังก์ชันเพื่อสร้างไฟล์ .docx และส่งออก
def export_terms_to_docx(terms):
    doc = Document()
    doc.add_heading('คำศัพท์', 0)

    for term in terms:
        doc.add_paragraph(f"คำศัพท์: {term[1]}")
        doc.add_paragraph(f"ความหมาย: {term[2]}")
        doc.add_paragraph("\n")

    byte_io = BytesIO()
    doc.save(byte_io)
    byte_io.seek(0)
    return byte_io

# ฟังก์ชันค้นหาความหมายจาก API พจนานุกรมภาษาอังกฤษ (Oxford Dictionary API)
def search_meaning_from_api(word):
    app_id = "eacd8799"  # กรอก Application ID ของคุณ
    app_key = "7b4b968a3bf970b446b2a470b0fdc3d8"  # กรอก Application Key ของคุณ
    url = f"https://od-api-sandbox.oxforddictionaries.com/api/v2/entries/en-us/{word.lower()}"
    
    headers = {
        'app_id': app_id,
        'app_key': app_key
    }

    try:
        # เพิ่ม timeout 10 วินาที
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "meanings" in data[0]:
                meaning = data[0]["meanings"][0]["definitions"][0]["definition"]
                return meaning
            else:
                return "ไม่พบความหมายจาก API"
        else:
            return f"ข้อผิดพลาดจาก API: {response.status_code} - {response.text}"

    except requests.exceptions.RequestException as e:
        # ข้อผิดพลาดในการเชื่อมต่อ
        return f"ไม่สามารถเชื่อมต่อกับ API ได้: {e}"

# ฟังก์ชันแสดงคำศัพท์ทั้งหมด
def display_terms_page():
    st.title('คำศัพท์ทั้งหมด')

    search_term = st.text_input("ค้นหาคำศัพท์", "")
    terms = show_terms(search_term)
    
    if terms:
        if st.button("ส่งออกเป็นไฟล์ .docx"):
            byte_io = export_terms_to_docx(terms)
            st.download_button(
                label="ดาวน์โหลดไฟล์ .docx",
                data=byte_io,
                file_name="terms.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        for term in terms:
            col1, col2, col3, col4 = st.columns([3, 3, 1, 1])
            with col1:
                st.text(term[1])  # คำศัพท์
            with col2:
                st.text(term[2])  # ความหมาย
            with col3:
                if st.button(f"แก้ไข", key=f"edit_{term[0]}"):
                    edit_term(term[0])
            with col4:
                if st.button(f"ลบ", key=f"delete_{term[0]}"):
                    delete_term(term[0])
                    st.success(f"คำศัพท์ '{term[1]}' ถูกลบแล้ว!")
                    st.experimental_rerun()

    else:
        st.write("ไม่พบคำศัพท์ที่ค้นหา.")

# หน้าเพิ่มคำศัพท์ใหม่
def add_term_page():
    st.title('เพิ่มคำศัพท์ใหม่')
    
    word = st.text_input("คำศัพท์:")
    option = st.radio("เลือกวิธีการกรอกความหมาย", ("กรอกความหมายเอง", "ใช้ความหมายจาก API"))
    
    if option == "กรอกความหมายเอง":
        definition = st.text_area("ความหมาย:") 
        
        if st.button('บันทึก'):
            if word and definition:
                add_term(word, definition)
                st.success(f"เพิ่มคำศัพท์ '{word}' สำเร็จ!")
            else:
                st.error("กรุณากรอกคำศัพท์และความหมาย.")
    
    elif option == "ใช้ความหมายจาก API":
        if word:
            definition = search_meaning_from_api(word)
            st.write(f"ความหมายจาก API: {definition}")
            
            if st.button('บันทึกคำศัพท์นี้'):
                add_term(word, definition)
                st.success(f"เพิ่มคำศัพท์ '{word}' สำเร็จ!")

# หน้าแก้ไขคำศัพท์
def edit_term(id):
    cursor.execute("SELECT word, definition FROM terms WHERE id = ?", (id,))
    term = cursor.fetchone()
    
    if term:
        word = st.text_input("คำศัพท์", term[0], max_chars=100)
        definition = st.text_area("ความหมาย", term[1], height=200)

        if st.button('บันทึกการแก้ไข'):
            update_term(id, word, definition)
            st.success(f"คำศัพท์ '{word}' ได้รับการแก้ไขแล้ว!")
    else:
        st.error("ไม่พบคำศัพท์ที่เลือก.")

# สร้างเมนูให้ผู้ใช้เลือกหน้า
def main():
    st.sidebar.title("เมนู")
    selection = st.sidebar.selectbox("เลือกหน้า", ["คำศัพท์ทั้งหมด", "เพิ่มคำศัพท์ใหม่"])

    if selection == "คำศัพท์ทั้งหมด":
        display_terms_page()
    elif selection == "เพิ่มคำศัพท์ใหม่":
        add_term_page()

if __name__ == '__main__':
    main()
