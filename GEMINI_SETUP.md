# 🤖 Gemini AI Integration Setup Guide

## 🎯 **What's New**

Your surveillance system now automatically generates **AI-powered reports** for every snapshot! Here's what you get:

### ✨ **Auto-Gemini Reports**
- **Every snapshot** gets an AI analysis
- **Brief, cost-effective** reports (under $0.0002 each!)
- **Object IDs included** for tracking
- **Activity descriptions** in natural language
- **Automatic display** in the web interface

### 🔍 **Vector Database Search**
- **Semantic search**: "Find suspicious activities"
- **Similarity matching**: "Show events like this one"
- **AI-powered queries**: Natural language search
- **Persistent storage**: All data saved and searchable

## 🚀 **Quick Setup**

### 1. **Get Your Gemini API Key**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key (starts with `AIza...`)

### 2. **Start the App**
```bash
cd web_app
python app.py
```

### 3. **Enable Gemini in Web Interface**
1. Open: `http://localhost:5002`
2. Check **"Enable Auto Gemini Reports"**
3. Enter your API key
4. Click **"Enable"**

### 4. **Start Processing**
1. Select camera or upload video
2. Click **"Start Processing"**
3. Watch AI reports appear automatically!

## 🎨 **What You'll See**

### **Timeline Events Now Include:**
- 📸 **Snapshot** (annotated + raw)
- 🤖 **AI Analysis** section with:
  - **Summary**: "Person walking near building entrance"
  - **Objects**: Car, Person, Building
  - **Object IDs**: 123, 456, 789
  - **Activity**: "Person approaching entrance"
  - **Confidence**: High/Medium/Low

### **Example AI Report:**
```
🤖 AI Analysis
├── Summary: Person walking near building entrance
├── Objects: person, building
├── Object IDs: 123, 456
├── Activity: Person approaching entrance
└── Confidence: high
```

## 💰 **Cost Breakdown**

| Usage | Daily Cost | Monthly Cost |
|-------|------------|--------------|
| 100 snapshots | $0.02 | $0.60 |
| 1,000 snapshots | $0.20 | $6.00 |
| 10,000 snapshots | $2.00 | $60.00 |

**Very affordable!** Each report costs less than 1/10th of a cent.

## 🔍 **Vector Search Examples**

### **Semantic Search:**
```bash
# Find suspicious activities
curl "http://localhost:5002/api/vector/search?q=person+loitering+entrance"

# Find all car-related events
curl "http://localhost:5002/api/vector/search?q=vehicle+parking+unauthorized"

# Find events similar to a specific incident
curl "http://localhost:5002/api/vector/search/similar/event_1234567890_789"
```

### **Web Interface:**
- **Auto-loads** Gemini reports for all timeline events
- **Real-time updates** when new events occur
- **Manual refresh** with "Load Report" buttons
- **Status display** shows cost and usage stats

## 🛠 **Troubleshooting**

### **Gemini Reports Not Appearing?**
1. ✅ Check API key is correct
2. ✅ Verify Gemini is enabled in web interface
3. ✅ Wait 2-3 seconds for reports to generate
4. ✅ Check browser console for errors

### **Vector Search Not Working?**
1. ✅ Ensure ChromaDB installed: `pip install chromadb`
2. ✅ Check vector database stats: `/api/vector/stats`
3. ✅ Verify events are being indexed

### **High Costs?**
1. ✅ Check usage stats: `/api/gemini/stats`
2. ✅ Disable Gemini if needed: Uncheck "Enable Auto Gemini Reports"
3. ✅ Clear old reports: `/api/gemini/clear`

## 🎉 **You're All Set!**

Your surveillance system now has:
- ✅ **AI-powered analysis** of every snapshot
- ✅ **Semantic search** capabilities
- ✅ **Cost-effective** operation
- ✅ **Beautiful web interface** with auto-updates
- ✅ **Persistent storage** in vector database

**No more manual prompting!** Everything happens automatically in the background. Just start processing and watch the AI reports appear! 🚀
