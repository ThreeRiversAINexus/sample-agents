# sample-agents

## Structure

### lmstudio.py

Represents a simple python interface to use with the LM studio server API.

### structured_chat.py

Represents a simple langchain v2 structured chat agent that has no external dependencies and an easy to edit prompt.

### fake_llm_examples

This project shows how to test langchain with fake LLM, so that you can test the code without actually calling out to any API or waiting for a real model to generate something, which may be inconsistent.

### flet_gen_ui

This was an experiment with generative UI that I completed. You can talk to this and it uses different UI elements in Flet as tools to modify its output. It can also generate images on demand. I like telling it to tell me a story, which it does in multiple bubbles.

### event_searcher

This app seeks out events that a user might like, which is the basis of my https://letsdo.agency app I've created; however, this is the baby version.

### discussion_show

This is an art show piece where we listen with whisper to conversations until we meet a certain threshold of context length. Then the AI generates images based on the current discussion. This is designed with NiceGUI and attempts to be compatible with PC and iOS devices.

### incomplete - rag/yags_master

This is an attempt to create a retrieval-augmented generation agent that assists with running gameplay for the open source role playing game "YAGS".

### incomplete - meta_prompting

This is supposed to be a basic tool for refining prompts by having the LLM critique and rewrite its own prompt.
