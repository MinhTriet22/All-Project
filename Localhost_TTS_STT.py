from flask import Flask, request, jsonify, send_from_directory
import os
from google.cloud import speech, texttospeech
import google.generativeai as genai

# --- SỬA ĐOẠN NÀY ---
# Lấy đường dẫn tuyệt đối đến thư mục chứa file script này
script_dir = os.path.dirname(os.path.abspath(__file__)) # NẾU CHẠY BẰNG GG COLAB HAY JUPITER NOTEBOOK PHẢI CHỈNH LẠI VÌ 2 CÁI NOTEBOOK ĐÓ KO CÓ SCRIPTT
# Ghép đường dẫn thư mục với tên file JSON
json_cred_path = os.path.join(
    script_dir, "YOUR_JSON_FILE")
# Đặt biến môi trường với đường dẫn tuyệt đối
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = json_cred_path
# --- KẾT THÚC SỬA ĐỔI ---

app = Flask(__name__)

# Các biến toàn cục
audio_is_ready = False
RECEIVED_AUDIO_FILENAME = "received_audio.wav"
RESPONSE_FILENAME = "voicedby.wav"
RECEIVED_IMAGE_FILENAME = "received_image.jpg"

# =================================================================
# CÁC HÀM TRỢ GIÚP (HELPER FUNCTIONS)
# =================================================================


def text_to_speech(text_to_speak):
    """Chuyển đổi văn bản thành file âm thanh voicedby.wav."""
    try:
        print(f"   --> Bắt đầu TTS cho văn bản: '{text_to_speak[:30]}...'")
        tts_client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text_to_speak)
        voice = texttospeech.VoiceSelectionParams(
            language_code="vi-VN",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000  # Đảm bảo khớp với ESP32
        )
        tts_response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        with open(RESPONSE_FILENAME, "wb") as out:
            out.write(tts_response.audio_content)
        print(f"   --> Đã tạo file âm thanh: {RESPONSE_FILENAME}")
        return True
    except Exception as e:
        print(f"   ### LỖI trong quá trình TTS: {e}")
        return False


# =================================================================
# CÁC ĐƯỜNG DẪN (FLASK ROUTES)
# =================================================================

@app.route('/uploadAudio', methods=['POST'])
def upload_audio_file():
    global audio_is_ready
    audio_is_ready = False
    print("\n-------------------------------------------")
    print("1. Nhận được yêu cầu upload âm thanh.")

    wav_data = request.data
    if not wav_data:
        print("   Lỗi: Không nhận được dữ liệu âm thanh.")
        return "No data received", 400

    try:
        # Lưu file nhận được
        with open(RECEIVED_AUDIO_FILENAME, 'wb') as f:
            f.write(wav_data)
        print(
            f"   Đã lưu file: {RECEIVED_AUDIO_FILENAME} ({len(wav_data)} bytes)")

        # 1. Google Speech-to-Text (STT)
        speech_client = speech.SpeechClient()
        with open(RECEIVED_AUDIO_FILENAME, "rb") as audio_file:
            audio_content = audio_file.read()
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="vi-VN"
        )
        response = speech_client.recognize(config=config, audio=audio)
        input_text = ""
        for result in response.results:
            input_text += result.alternatives[0].transcript
        # Thêm dấu nháy để dễ thấy chuỗi rỗng
        print(f"   Văn bản nhận diện: '{input_text}'")

        # --- THÊM ĐOẠN KIỂM TRA NÀY ---
        if not input_text.strip():
            print("   Lỗi: Không nhận diện được giọng nói hoặc chỉ có sự im lặng.")
            # Tạo một file âm thanh báo lỗi để gửi về ESP32
            error_text = "Xin lỗi, tôi không nghe rõ bạn nói gì. Vui lòng thử lại."
            text_to_speech(error_text)  # Gọi hàm TTS với câu báo lỗi
            audio_is_ready = True  # Báo sẵn sàng để ESP32 tải file lỗi về
            return "No speech detected in audio", 200  # Trả về 200 OK
        # --- KẾT THÚC ĐOẠN KIỂM TRA ---

        # 2. Gửi nội dung lên Gemini API
        genai.configure(api_key="yOUR_API")
        # --- SỬA DÒNG NÀY ---
        model = genai.GenerativeModel(
            "gemini-2.0-flash")  # Đổi từ "gemini-pro"
        # -------------------
        gemini_reply = model.generate_content(input_text)
        output_text = gemini_reply.text
        print(f"   Gemini trả lời: {output_text}")

        # 3. Google Text-to-Speech (TTS)
        # --- THAY THẾ TOÀN BỘ LOGIC TTS CŨ BẰNG LỆNH GỌI HÀM NÀY ---
        text_to_speech(output_text)
        # -----------------------------------------------------------

        # Báo hiệu đã xử lý xong
        audio_is_ready = True
        print("   Trạng thái âm thanh: ĐÃ SẴN SÀNG")
        return "Audio upload & AI process successful", 200

    except Exception as e:
        print(f"   Lỗi khi xử lý file âm thanh: {e}")
        return "Error processing audio file", 500


@app.route('/checkStatus', methods=['GET'])
def check_status():
    global audio_is_ready
    if audio_is_ready:
        print("2. Kiểm tra trạng thái: Trả về 'ready'")
        return jsonify({"status": "ready"})
    else:
        print("2. Kiểm tra trạng thái: Trả về 'processing'")
        return jsonify({"status": "processing"})


@app.route('/voicedby.wav', methods=['GET'])
def download_response_file():
    global audio_is_ready
    print(f"3. Nhận được yêu cầu tải file {RESPONSE_FILENAME}. Đang gửi...")
    try:
        audio_is_ready = False
        return send_from_directory(directory='.', path=RESPONSE_FILENAME, as_attachment=True)
    except FileNotFoundError:
        print(f"   Lỗi: Không tìm thấy file {RESPONSE_FILENAME}")
        return "File not found", 404


@app.route('/uploadImage', methods=['POST'])
def upload_image_file():
    print("\n-------------------------------------------")
    print("Nhận được yêu cầu upload ảnh.")
    image_data = request.data
    if not image_data:
        print("   Lỗi: Không nhận được dữ liệu ảnh.")
        return "No image data received", 400
    try:
        with open(RECEIVED_IMAGE_FILENAME, 'wb') as f:
            f.write(image_data)
        print(
            f"   Đã lưu file ảnh: {RECEIVED_IMAGE_FILENAME} ({len(image_data)} bytes)")
        return "Image received successfully", 200
    except Exception as e:
        print(f"   Lỗi khi lưu file ảnh: {e}")
        return "Error saving image file", 500


if __name__ == '__main__':
    port = 5000
    print("===================================================")
    print(f" Server đa chức năng đang chạy tại http://0.0.0.0:{port}")
    print(" Các đường dẫn hoạt động:")
    print(f" - POST -> /uploadAudio  (Nhận file âm thanh)")
    print(f" - GET  -> /checkStatus  (Kiểm tra trạng thái âm thanh)")
    print(f" - GET  -> /voicedby.wav (Gửi lại file âm thanh)")
    print(f" - POST -> /uploadImage  (Nhận file ảnh)")
    print("===================================================")
    print("Nhấn Ctrl+C để dừng server.")
    app.run(host='0.0.0.0', port=port, debug=False)
