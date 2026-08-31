import streamlit as st
import pandas as pd
import json
from io import BytesIO
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")  
client = genai.Client(api_key="api_key")
MODEL_NAME = "gemini-3.7-flash"  


class Customer():
    def __init__(self,name):
        self.name = name
        self.answer = {}
        self.score = 0
        self.status = "Unqualified"
    def add_answer(self,key,value):
        self.answer[key] = value

    def calculate_score(self):
        score = 0
        try:
            budget = int(self.answer.get("budget", 0))
            if budget >= 5000:
                score += 2
        except ValueError:
            pass
        timeline = self.answer.get("timeline", "").lower()
        if "week" in timeline or "urgent" in timeline:
            score += 2

        need = self.answer.get("need", "").lower()
        if len(need) > 5:
            score += 3

        self.score = score

        if self.score >= 6:
            self.status = "Qualified"
        elif self.score >= 3:
            self.status = "Potential"
        else:
            self.status = "Unqualified"

    def summary(self):
       return {
           "name": self.name,
            "answers": self.answer,
            "score": self.score,
            "status": self.status
           
    }

    

def save_customer(customer, filename="leads.json"):
    try:
        with open(filename, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []

    data.append(customer.summary())

    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

def load_leads(filename="leads.json"):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def generate_sales_note(customer):
    prompt = f"""
    Generate a concise sales note for the following customer:
    Name: {customer.name}
    Answers: {customer.answer}
    Score: {customer.score}
    Status: {customer.status}
    """
    try:
       response = client.models.generate_content(
    model=MODEL_NAME,
    contents=[{"role": "user", "parts": [{"text": prompt}]}]
       )
       note = response.text.strip()

       return response.text.strip()
    except Exception as e:
        return f"Error generating sales note: {str(e)}"


def run_app():
    st.title("💬 Lead Qualification Chatbot (Google GenAI)")
    st.caption("Qualify leads, generate sales notes, analyze data, and export reports.")

    tab1, tab2 = st.tabs(["Chatbot", "Analytics & Reports"])

    with tab1:
        name = st.text_input("Enter customer name:")
        budget = st.text_input("What is your budget (USD)?")
        timeline = st.text_input("When do you need the product/service?")
        need = st.text_area("What problem are you trying to solve?")

        if st.button("Submit Lead"):
            if not name:
                st.error("Please enter a name.")
                return

            customer = Customer(name)
            customer.add_answer("budget", budget)
            customer.add_answer("timeline", timeline)
            customer.add_answer("need", need)

            customer.calculate_score()
            summary = customer.summary()

            st.subheader("📊 Lead Summary")
            st.json(summary)

            save_customer(customer)
            st.success("✅ Lead saved locally!")

            # Generate sales note with Gemini
            note = generate_sales_note(customer)
            st.subheader("📝 Sales Note (Gemini)")
            st.write(note)

    with tab2:
        st.subheader("📈 Lead Analytics")
        leads = load_leads()

        if leads:
            df = pd.DataFrame(leads)

            # Lead status distribution
            st.write("### Lead Status Distribution")
            st.bar_chart(df["status"].value_counts())
            if "status" in df.columns:
                st.write("### Lead Status Distribution")
                st.bar_chart(df["status"].value_counts())
            else:
                st.info("No status data available yet.")



            # Average budget by status
            budgets = []
            statuses = []
            for lead in leads:
                try:
                    budgets.append(int(lead["answers"].get("budget", 0)))
                    statuses.append(lead["status"])
                except ValueError:
                    continue
            if budgets:
                budget_df = pd.DataFrame({"Budget": budgets, "Status": statuses})
                st.write("### Average Budget by Lead Status")
                st.bar_chart(budget_df.groupby("Status")["Budget"].mean())

            # Timeline entries
            timelines = [lead["answers"].get("timeline", "") for lead in leads]
            timeline_df = pd.DataFrame({"Timeline": timelines})
            st.write("### Timeline Entries")
            st.table(timeline_df.value_counts().reset_index(name="Count"))
            st.write("### 📂 Export Leads")
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download Leads as CSV",
                data=csv,
                file_name="leads_report.csv",
                mime="text/csv"
            )

            # Export Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Leads")
            st.download_button(
                label="⬇️ Download Leads as Excel",
                data=output.getvalue(),
                file_name="leads_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No leads yet. Submit some in the chatbot tab.")


if __name__ == "__main__":
    run_app()