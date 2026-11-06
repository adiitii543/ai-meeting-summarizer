# ==========================================
# AI MEETING SUMMARIZER
# ==========================================

import os
import requests
import gradio as gr
from pypdf import PdfReader

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"
WHISPER_MODEL_SIZE = "base"  # use "small" for better Hindi

_whisper_model = None


def get_whisper_model():
    """Load Whisper only when audio is actually used."""
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)
    return _whisper_model


# ------------------------------------------
# OLLAMA
# ------------------------------------------

def ask_ollama(prompt):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=300,
        )
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        return f"❌ Ollama Error: {e}"


# ------------------------------------------
# MEETING SUMMARIZATION
# ------------------------------------------

def summarize_meeting(transcript, language="English"):
    prompt = f"""
You are a professional AI meeting assistant.

Analyze the meeting transcript and create a clear,
professional meeting report.

The transcript may be in any language.
Write the entire report in {language}.

Use exactly these sections:

# MEETING SUMMARY
Give a concise summary of the meeting.

# KEY DISCUSSION POINTS
List the important topics discussed.

# DECISIONS MADE
List only decisions explicitly mentioned.
Do not invent decisions.

# ACTION ITEMS
For every task mentioned, provide:
- Task
- Responsible person
- Deadline

If information is unavailable, write "Not specified".

# DEADLINES
List all deadlines mentioned.

# UNRESOLVED ISSUES
List questions, problems, or decisions that remain unresolved.

IMPORTANT:
- Do not invent information.
- Use only information present in the transcript.
- Keep the report clear and professional.

MEETING TRANSCRIPT
==================
{transcript}
==================
"""
    return ask_ollama(prompt)


# ------------------------------------------
# AUDIO TRANSCRIPTION
# ------------------------------------------

def transcribe_audio(audio_file):
    try:
        result = get_whisper_model().transcribe(audio_file)
        return result["text"]
    except Exception as e:
        return f"❌ Transcription Error: {e}"


# ------------------------------------------
# FILE TEXT EXTRACTION
# ------------------------------------------

def extract_text(file_path):
    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".txt":
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()

    elif extension == ".pdf":
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    return ""


# ------------------------------------------
# MAIN PROCESS
# ------------------------------------------

def process_meeting(pasted_text, document_file, audio_file, language):
    if pasted_text and pasted_text.strip():
        transcript = pasted_text.strip()
    elif document_file:
        transcript = extract_text(document_file)
    elif audio_file:
        transcript = transcribe_audio(audio_file)
    else:
        return "❌ Please provide a transcript, document, or audio file."

    if not transcript.strip():
        return "❌ No text could be extracted."

    if transcript.startswith("❌"):
        return transcript

    return summarize_meeting(transcript, language)


# ------------------------------------------
# GRADIO INTERFACE
# ------------------------------------------

with gr.Blocks(title="AI Meeting Summarizer") as demo:

    gr.Markdown("""
    # 🤖 AI Meeting Summarizer

    **Transform meeting transcripts, documents, and recordings
    into structured meeting reports using AI.**
    """)

    with gr.Row():

        with gr.Column():
            gr.Markdown("### 📥 Meeting Input")

            text_input = gr.Textbox(
                label="Meeting Transcript",
                placeholder="Paste your meeting transcript here...",
                lines=12,
            )

            document_input = gr.File(
                label="Upload TXT / PDF",
                file_types=[".txt", ".pdf"],
                type="filepath",
            )

            audio_input = gr.Audio(
                label="Upload Meeting Recording",
                sources=["upload"],
                type="filepath",
            )

            language_input = gr.Dropdown(
                choices=["English", "Hindi", "Spanish", "French",
                         "German", "Italian", "Portuguese", "Thai"],
                value="English",
                label="Report Language",
            )

            summarize_button = gr.Button(
                "🚀 Generate Meeting Report", variant="primary"
            )

        with gr.Column():
            gr.Markdown("### 📊 Meeting Report")
            output = gr.Markdown(value="Your meeting report will appear here.")

    summarize_button.click(
        fn=process_meeting,
        inputs=[text_input, document_input, audio_input, language_input],
        outputs=output,
    )


if __name__ == "__main__":
    demo.launch(share=True)
