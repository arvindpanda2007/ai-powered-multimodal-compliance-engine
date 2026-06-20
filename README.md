# ai-powered-multimodal-compliance-engine
AI-powered multimodal compliance engine that analyzes video, audio, and on-screen text using OCR, RAG, LangGraph, and LLMs to detect regulatory violations and generate structured compliance reports with LangSmith-based observability and evaluation.

This project implements an AI-powered Multimodal Compliance Engine that automates the auditing of video content against regulatory and organizational compliance standards. The system leverages speech-to-text transcription and OCR pipelines to extract information from video and on-screen content, which is then enriched through a Retrieval-Augmented Generation (RAG) architecture to retrieve relevant compliance policies and regulatory guidelines.

The core workflow is orchestrated using LangGraph, enabling modular, scalable, and deterministic agent execution across ingestion, retrieval, reasoning, and reporting stages. Semantic search is powered by vector embeddings and hybrid retrieval techniques to identify the most relevant compliance rules for each piece of content. An LLM-based reasoning layer evaluates the extracted evidence against these rules and generates structured compliance assessments, violation explanations, severity classifications, and actionable recommendations.

To ensure production-grade reliability and observability, LangSmith is integrated for workflow tracing, prompt inspection, debugging, evaluation, and performance monitoring across the entire agent pipeline. The platform ultimately transforms unstructured video data into structured JSON compliance reports, providing transparency, auditability, and operational insights for compliance teams.

