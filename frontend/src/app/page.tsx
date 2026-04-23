"use client";

import React, { useMemo, useState, useRef, useEffect } from "react";
import { askQuestion, uploadPdf } from "@/lib/api";
import { getOrCreateUserId } from "@/lib/user";

type Citation = { doc_id: string; page?: number | null; chunk_id: string; score?: number | null };

type Message = {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  timestamp: Date;
};

export default function HomePage() {
  const [userId, setUserId] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [question, setQuestion] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [uploadingBusy, setUploadingBusy] = useState<boolean>(false);
  const [askingBusy, setAskingBusy] = useState<boolean>(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const apiBase = useMemo(() => process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000", []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function ensureUser() {
    const id = await getOrCreateUserId();
    setUserId(id);
    return id;
  }


  async function onAsk() {
    const q = question.trim();
    if (!q) {
      addSystemMessage("Please enter a question.");
      return;
    }

    // Add user message
    const userMsg: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: q,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setQuestion("");

    setAskingBusy(true);
    try {
      await ensureUser();
      const res = await askQuestion(q);

      // Add assistant message
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: res.answer || "No answer provided.",
        citations: res.citations || [],
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (e: any) {
      addSystemMessage(`✗ Error: ${e?.message || String(e)}`);
    } finally {
      setAskingBusy(false);
    }
  }

  function addSystemMessage(content: string) {
    const msg: Message = {
      id: Date.now().toString(),
      type: 'system',
      content,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, msg]);
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];

      // Only accept PDFs
      if (!droppedFile.type.includes('pdf')) {
        addSystemMessage('✗ Please upload PDF files only');
        return;
      }

      setFile(droppedFile);

      // Auto-upload immediately
      setUploadingBusy(true);
      try {
        await ensureUser();
        const res = await uploadPdf(droppedFile);
        addSystemMessage(`✓ Successfully uploaded! Document ID: ${res.doc_id}`);
        setFile(null);
      } catch (e: any) {
        addSystemMessage(`✗ Upload failed: ${e?.message || String(e)}`);
        setFile(null);
      } finally {
        setUploadingBusy(false);
      }
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);

      // Auto-upload immediately
      setUploadingBusy(true);
      try {
        await ensureUser();
        const res = await uploadPdf(selectedFile);
        addSystemMessage(`✓ Successfully uploaded! Document ID: ${res.doc_id}`);
        setFile(null);
        // Reset file input
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      } catch (e: any) {
        addSystemMessage(`✗ Upload failed: ${e?.message || String(e)}`);
        setFile(null);
      } finally {
        setUploadingBusy(false);
      }
    }
  };

  return (
    <div
      className="flex flex-col h-screen"
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {dragActive && (
        <div className="fixed inset-0 z-50 bg-purple-900/30 backdrop-blur-sm flex items-center justify-center">
          <div className="bg-slate-900 border-2 border-dashed border-purple-500 rounded-2xl p-12 text-center">
            <svg className="w-16 h-16 text-purple-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-xl font-semibold text-slate-100">Drop PDF here to upload</p>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="border-b border-slate-800/60 bg-black/80 backdrop-blur-md shrink-0">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-3 pb-4">
          <div className="text-center">
            <h1 className="text-4xl md:text-5xl font-black bg-gradient-to-r from-purple-400 via-fuchsia-400 to-blue-400 bg-clip-text text-transparent mb-1 py-2 leading-tight" style={{ filter: 'drop-shadow(0 0 25px rgba(168, 85, 247, 0.5))', WebkitTextFillColor: 'transparent' }}>
              PaperTrail AI
            </h1>
            <p className="text-sm md:text-base text-slate-300 font-medium">Knowledge Graph-Powered Document Intelligence</p>
          </div>
        </div>
      </header>

      {/* Chat Messages Area */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {messages.length === 0 ? (
            <div className="text-center py-16">
              <div className="inline-flex p-4 rounded-full bg-slate-800 mb-4">
                <svg className="w-12 h-12 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Start your paper trail</h3>
              <p className="text-slate-300 max-w-md mx-auto">Upload a PDF and ask questions — PaperTrail AI traces connections across your documents using a knowledge graph</p>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.type === 'system' ? (
                    <div className="max-w-2xl w-full p-3 rounded-lg bg-slate-800 border border-slate-600 text-sm text-slate-100">
                      {msg.content}
                    </div>
                  ) : msg.type === 'user' ? (
                    <div className="max-w-2xl bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-2xl px-4 py-3 shadow-lg">
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  ) : (
                    <div className="max-w-3xl w-full bg-slate-900 backdrop-blur-sm rounded-2xl shadow-lg shadow-black/50 border border-slate-600 overflow-hidden">
                      <div className="p-6">
                        <div className="prose prose-slate max-w-none">
                          <p className="text-white leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                        </div>

                        {msg.citations && msg.citations.length > 0 && (
                          <div className="mt-6 pt-6 border-t border-slate-700">
                            <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              Sources ({msg.citations.length})
                            </h4>
                            <div className="grid sm:grid-cols-2 gap-3">
                              {msg.citations.map((c) => (
                                <div
                                  key={c.chunk_id}
                                  className="p-3 rounded-lg bg-slate-800 border border-slate-600 hover:border-purple-500 hover:bg-purple-900/30 transition-all"
                                >
                                  <div className="flex items-start gap-2">
                                    <svg className="w-4 h-4 text-slate-300 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    <div className="flex-1 min-w-0">
                                      <p className="text-xs font-mono text-slate-200 truncate">{c.doc_id.slice(0, 16)}...</p>
                                      <div className="flex items-center gap-2 mt-1">
                                        <span className="text-xs text-slate-300">Page {c.page ?? "?"}</span>
                                        {typeof c.score === "number" && (
                                          <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/30 text-purple-200">
                                            {(c.score * 100).toFixed(0)}% match
                                          </span>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
      </main>

      {/* Fixed Bottom Input Area */}
      <footer className="border-t border-slate-800/60 bg-black/80 backdrop-blur-md shrink-0">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          {/* File Upload Status */}
          {file && (
            <div className="mb-3 flex items-center gap-2 px-3 py-2 rounded-lg bg-purple-500/10 border border-purple-500/30">
              <svg className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="text-sm text-purple-300 flex-1">{file.name}</span>
              <span className="text-xs text-purple-400">{(file.size / 1024).toFixed(1)} KB</span>
              <button
                onClick={() => setFile(null)}
                className="text-purple-400 hover:text-purple-300"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          )}

          {/* Input Area */}
          <div className="flex items-end gap-2">
            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              onChange={handleFileChange}
              disabled={uploadingBusy}
              className="hidden"
            />

            {/* Upload Button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadingBusy}
              className="shrink-0 p-3 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-purple-500 text-slate-300 hover:text-purple-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              title="Attach PDF (uploads automatically)"
            >
              {uploadingBusy ? (
                <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
              )}
            </button>

            {/* Textarea */}
            <textarea
              ref={textareaRef}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask anything about your uploaded documents…"
              rows={1}
              disabled={askingBusy}
              className="flex-1 px-4 py-3 rounded-xl bg-slate-800 border border-slate-600 text-white placeholder:text-slate-400 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/50 outline-none transition-all resize-none disabled:opacity-50 disabled:cursor-not-allowed text-lg"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey && !askingBusy) {
                  e.preventDefault();
                  onAsk();
                }
              }}
              style={{ minHeight: '48px', maxHeight: '200px' }}
            />

            {/* Send Button */}
            <button
              onClick={onAsk}
              disabled={askingBusy || !apiBase || !question.trim()}
              className="shrink-0 p-3 rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-purple-500/30 hover:shadow-xl hover:shadow-purple-500/40"
              title="Send message (Enter)"
            >
              {askingBusy ? (
                <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>

          {/* Helper Text */}
          <p className="mt-2 text-xs text-slate-400 text-center">
            Press Enter to send • Shift+Enter for new line • PDFs upload automatically when selected
          </p>
        </div>
      </footer>
    </div>
  );
}
