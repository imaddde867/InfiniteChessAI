import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import json

def load_and_prepare_data():
    with open('chess_training_data.json', 'r') as f:
        data = json.load(f)
    
    # Convert to format expected by trainer
    formatted_texts = []
    for example in data:
        # Combine messages into training text
        text = ""
        for msg in example['messages']:
            text += f"<|{msg['role']}|>\n{msg['content']}\n\n"
        text += "<|end|>"
        formatted_texts.append({"text": text})
    
    return Dataset.from_list(formatted_texts)

def setup_model_and_tokenizer(model_name="microsoft/DialoGPT-medium"):  # Will try Llama later
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto"
    )
    
    # Add padding token if needed
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    return model, tokenizer

def tokenize_function(examples, tokenizer):
    return tokenizer(
        examples["text"],
        truncation=True,
        padding=True,
        max_length=512,
        return_tensors="pt"
    )

def train_chess_ai():
    # Load data
    dataset = load_and_prepare_data()
    
    # Setup model
    model, tokenizer = setup_model_and_tokenizer()
    
    # Tokenize
    tokenized_dataset = dataset.map(
        lambda x: tokenize_function(x, tokenizer),
        batched=True
    )
    
    # LoRA configuration for efficient fine-tuning
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.1,
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    model = get_peft_model(model, peft_config)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir="./chess-ai-model",
        num_train_epochs=3,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir="./logs",
        logging_steps=100,
        save_steps=1000,
        evaluation_strategy="steps",
        eval_steps=1000,
        save_total_limit=2,
        remove_unused_columns=False,
        push_to_hub=False,
        report_to="none",  # Disable wandb for now
    )
    
    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
    )
    
    # Train
    trainer.train()
    
    # Save
    trainer.save_model()
    tokenizer.save_pretrained("./chess-ai-model")

if __name__ == "__main__":
    train_chess_ai()