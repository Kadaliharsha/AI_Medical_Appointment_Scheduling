# 🏥 AI Medical Scheduling Agent - Demo Guide

## 🚀 Quick Start

### 1. **CLI Version** (Current Working)
```bash
python app/main.py
```

### 2. **Web UI Version** (New!)
```bash
python run_streamlit.py
```
Then open: http://localhost:8501

## 🎬 Demo Video Script

### **Scene 1: Introduction (30 seconds)**
- Show the beautiful Streamlit UI
- Highlight key features in sidebar
- Explain the AI agent's capabilities

### **Scene 2: Complete Booking Flow (3 minutes)**

#### **Step 1: Patient Greeting**
- User: "I'd like to book an appointment"
- AI: Collects name, DOB, doctor preference, location

#### **Step 2: Patient Lookup**
- AI: Searches EMR database
- Shows: "Found Aarav Sharma - New Patient (60min slot required)"

#### **Step 3: Smart Scheduling**
- AI: Shows available Calendly slots
- User: Selects preferred time
- AI: Books appointment through Calendly integration

#### **Step 4: Insurance Collection**
- AI: Collects carrier, member ID, group ID
- Shows: Insurance information stored

#### **Step 5: Form Distribution**
- AI: Sends intake forms via email
- Shows: "Forms sent to patient@email.com"

#### **Step 6: Enhanced Reminders**
- AI: Schedules 3 automated reminders
- Shows: Reminder timeline and actions

### **Scene 3: Edge Cases (1 minute)**
- Show error handling for unavailable slots
- Demonstrate returning patient (30min slot)
- Show system status and tool availability

### **Scene 4: Summary (30 seconds)**
- Show booking confirmation
- Highlight all completed steps
- Mention real-world integration possibilities

## 🎯 Key Features to Highlight

### ✅ **Core Requirements Met**
- [x] Patient Greeting & Lookup
- [x] Smart Scheduling (60min new, 30min returning)
- [x] Calendly Integration (simulated)
- [x] Insurance Collection
- [x] Form Distribution
- [x] Enhanced Reminder System (3 reminders with actions)

### 🔧 **Technical Features**
- [x] LangChain + OpenAI integration
- [x] Tool-based architecture
- [x] Error handling
- [x] Session management
- [x] Modern UI with Streamlit

## 📱 UI Features

### **Main Interface**
- **Chat Interface**: Natural conversation flow
- **Feature Cards**: Visual representation of capabilities
- **Booking Summary**: Real-time appointment details
- **System Status**: API and tool availability

### **Sidebar**
- **Key Features**: Overview of agent capabilities
- **Reset Button**: Clear conversation history
- **Quick Start**: Example messages for users

## 🎥 Recording Tips

1. **Use Full Screen**: Record the entire browser window
2. **Clear Audio**: Speak clearly and at moderate pace
3. **Show Tool Calls**: Highlight when AI uses tools
4. **Demonstrate Errors**: Show how system handles edge cases
5. **End with Success**: Complete a full booking flow

## 📊 Success Metrics

- ✅ **Functional Demo**: Complete patient booking workflow
- ✅ **Data Accuracy**: Correct patient classification and scheduling
- ✅ **Integration Success**: Excel exports and calendar management
- ✅ **Code Quality**: Clean, documented, executable codebase

## 🚀 Next Steps

1. **Record Demo Video** (3-5 minutes)
2. **Create Technical Document** (1-page PDF)
3. **Package Code** (ZIP with all files)
4. **Submit to RagaAI** (chaithra.mk@raga.ai)

---

**Ready to create an impressive demo! 🎬**
