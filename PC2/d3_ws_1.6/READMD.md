# README

## 1. Project Overview
This project is a ROS 2-based voice ordering robot system.
It captures user speech, converts it to text through STT, and combines GPT-based dialogue logic with Vector DB retrieval to determine the final cocktail menu and recipe code.

Main goals:
- Automate voice-based cocktail ordering and recommendation
- Publish a robot control recipe code when an order is confirmed
- Handle voice interaction for cup cleanup confirmation (ASK_TRIGGER)

---

## 2. Tech Stack
- ROS 2 (rclpy, Action Server, Publisher/Subscriber)
- OpenAI API (Whisper STT, GPT, TTS)
- ChromaDB (local vector database)
- PyAudio (microphone input)

---

## 3. Package Structure
### 3.1 cocktail_order_interfaces
- Role: Defines interface contracts between nodes
- Includes:
  - CocktailOrder.action
  - TriggerCleanup.srv

### 3.2 cocktail_order_pkg
- Role: Runtime package for integrated order logic
- Core modules:
  - integrated_order_node.py: Main orchestration node
  - MicController.py: Microphone stream control
  - wakeup_word.py: Wake-word detection
  - stt.py: Whisper STT integration
  - tts.py: TTS generation/playback
  - build_db.py: Cocktail Vector DB builder

### 3.3 Console Entry Points
- order_node: Runs the integrated order node
- build_db: Rebuilds the local vector database

---

## 4. Directory Layout
```text
d3_ws_1.6/
  src/
    cocktail_order_interfaces/
    cocktail_order_pkg/
  build/
  install/
  log/
```

---

## 5. Prerequisites
### 5.1 Required Environment
- Linux with ROS 2 installed
- Connected audio input device (microphone)

### 5.2 Environment Variables
You must set an OpenAI API key for STT/GPT/TTS features.

```bash
export OPENAI_API_KEY="YOUR_API_KEY"
```

To persist it in your shell profile:
```bash
echo 'export OPENAI_API_KEY="YOUR_API_KEY"' >> ~/.bashrc
source ~/.bashrc
```

---

## 6. Build and Run
### 6.1 Build Workspace
```bash
cd /home/rokey/d3_ws_1.6
colcon build
```

### 6.2 Source Environment
```bash
source /home/rokey/d3_ws_1.6/install/setup.bash
```

### 6.3 Build Vector DB (first run or refresh)
```bash
ros2 run cocktail_order_pkg build_db
```

### 6.4 Run Integrated Order Node
```bash
ros2 run cocktail_order_pkg order_node
```

---

## 7. Runtime Interfaces
### 7.1 Action: cocktail_order
- Goal:
  - start_chat (bool)
- Result:
  - is_success (bool)
  - final_menu (string)
  - recipe_code (string)
- Feedback:
  - current_turn (int32)
  - user_text (string)
  - bot_message (string)

### 7.2 Service: TriggerCleanup
- Request:
  - cup_id (int32)
- Response:
  - success (bool)

### 7.3 Main Topics
- Subscribe:
  - /cup_cleanup/ask_trigger
- Publish:
  - /cup_cleanup/robot_feedback
  - /cup_cleanup/trigger
  - /robot_recipe_trigger

---

## 8. Main Runtime Scenarios
### 8.1 Order Dialogue
1. Detect wake-word in IDLE state
2. Record user speech and run STT
3. Evaluate GPT state (chat/recommend/confirm/success)
4. Publish recipe_code when state reaches success
5. Return to IDLE after session ends

### 8.2 Cup Cleanup Confirmation
1. Receive /cup_cleanup/ask_trigger event
2. Ask user for cleanup confirmation via TTS
3. Analyze spoken response with STT and decide approve/reject
4. Publish the result to feedback topics

---

## 9. Tuning Guide
Adjust the following values depending on environment and noise conditions.

### 9.1 Microphone/Recording
- VOLUME_THRESHOLD: base noise threshold
- dynamic_threshold: dynamic noise baseline
- SILENCE_LIMIT: end-of-speech detection window
- TIMEOUT_LIMIT: wait timeout
- MAX_RECORD_TIME: max recording duration

### 9.2 Dialogue Quality
- GPT temperature: controls recommendation style (conservative vs creative)
- MAX_TURN: max turns before order confirmation

---

## 10. Operational Recommendations
- Externalize device index (device_index), external API address, and thresholds using ROS parameters or .env instead of hardcoding
- Improve exception logging granularity for easier failure analysis
- Validate multi-threaded state transition synchronization (IDLE/in-dialogue/cleanup-confirmation) before production deployment

---

## 11. Troubleshooting
### 11.1 OpenAI API Errors
- Symptom: STT/GPT/TTS calls fail
- Check:
  1. OPENAI_API_KEY is set correctly
  2. Network connectivity
  3. API quota and permission status

### 11.2 Audio Input Errors
- Symptom: microphone open failure or no recording response
- Check:
  1. Microphone connection status
  2. device_index configuration
  3. PyAudio and audio driver health

### 11.3 ROS Interface Resolution Errors
- Symptom: action/srv import failure
- Check:
  1. Re-run colcon build
  2. Re-source install/setup.bash
  3. Verify build order and dependency setup for both packages

---

## 12. Quick Checklist
- OPENAI_API_KEY configured
- colcon build completed successfully
- install/setup.bash sourced
- build_db executed (if needed)
- order_node launched and logs verified
