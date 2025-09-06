import torch
import json
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers import TrainingArguments, Trainer
import os
from pathlib import Path

# Set environment variables to avoid mutex issues
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"

# Disable MPS backend if it's causing issues
if torch.backends.mps.is_available():
    print("MPS backend available but setting to CPU to avoid mutex issues")
    torch.backends.mps.is_built = False

class ChessDataset(Dataset):
    """Custom dataset class for chess training data"""
    
    def __init__(self, jsonl_path, tokenizer, max_length=512):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.examples = []
        
        # Load your JSONL data
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line.strip())
                self.examples.append(data)
    
    def __len__(self):
        return len(self.examples)
    
    def __getitem__(self, idx):
        example = self.examples[idx]
        
        # Combine prompt and completion for training
        full_text = example['prompt'] + example['completion']
        
        # Tokenize the text
        encoding = self.tokenizer(
            full_text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        # For causal language modeling, labels are the same as input_ids
        # but we mask the prompt part so loss is only calculated on completion
        input_ids = encoding['input_ids'].squeeze()
        attention_mask = encoding['attention_mask'].squeeze()
        
        # Create labels (same as input_ids for causal LM)
        labels = input_ids.clone()
        
        # Find where the completion starts to mask prompt in loss calculation
        prompt_tokens = self.tokenizer(example['prompt'], add_special_tokens=False)['input_ids']
        prompt_length = len(prompt_tokens)
        
        # Mask the prompt tokens in labels (-100 means ignore in loss)
        labels[:prompt_length] = -100
        
        return {
            'input_ids': input_ids,
            'attention_mask': attention_mask,
            'labels': labels
        }

def create_data_loader(jsonl_path, tokenizer, batch_size=4, max_length=512):
    dataset = ChessDataset(jsonl_path, tokenizer, max_length)
    return DataLoader(dataset, batch_size=batch_size, shuffle=True)

def setup_model_and_tokenizer(model_name="microsoft/DialoGPT-medium"):
    """
    Load pre-trained model and tokenizer
    Start with DialoGPT-medium for testing, then upgrade to larger models
    """
    
    print(f"Loading model: {model_name}")
    
    # Load tokenizer
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # Add padding token if it doesn't exist
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    
    # Load model with CPU only to avoid MPS issues
    print("Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float32,  # Use float32 instead of float16
        device_map=None,  # Load on CPU first
        trust_remote_code=True
    )
    
    # Resize token embeddings if we added new tokens
    model.resize_token_embeddings(len(tokenizer))
    
    print("Model and tokenizer loaded successfully!")
    return model, tokenizer

def count_parameters(model):
    """Count total and trainable parameters"""
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total parameters: {total:,}")
    print(f"Trainable parameters: {trainable:,}")
    return total, trainable

class ChessTrainer:
    def __init__(self, model, tokenizer, train_dataloader, val_dataloader=None):
        self.model = model
        self.tokenizer = tokenizer
        self.train_dataloader = train_dataloader
        self.val_dataloader = val_dataloader
        
        # Use CPU to avoid MPS mutex issues
        self.device = torch.device("cpu")
        print(f"Using device: {self.device}")
        
        # Move model to device
        self.model.to(self.device)
        
        # Setup optimizer (AdamW is standard for transformer fine-tuning)
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=5e-5,  # Learning rate - start conservative
            weight_decay=0.01  # Regularization to prevent overfitting
        )
        
        # Setup learning rate scheduler (optional but recommended)
        self.scheduler = torch.optim.lr_scheduler.LinearLR(
            self.optimizer,
            start_factor=1.0,
            end_factor=0.1,
            total_iters=len(train_dataloader) * 3  # 3 epochs
        )
    
    def train_epoch(self):
        """Train for one epoch"""
        self.model.train()
        total_loss = 0
        num_batches = len(self.train_dataloader)
        
        for batch_idx, batch in enumerate(self.train_dataloader):
            # Move batch to device
            input_ids = batch['input_ids'].to(self.device)
            attention_mask = batch['attention_mask'].to(self.device)
            labels = batch['labels'].to(self.device)
            
            # Zero gradients
            self.optimizer.zero_grad()
            
            # Forward pass
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )
            
            loss = outputs.loss
            
            # Backward pass
            loss.backward()
            
            # Gradient clipping (prevents exploding gradients)
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            
            # Update weights
            self.optimizer.step()
            self.scheduler.step()
            
            total_loss += loss.item()
            
            # Print progress
            if batch_idx % 100 == 0:
                avg_loss = total_loss / (batch_idx + 1)
                print(f"Batch {batch_idx}/{num_batches}, Loss: {avg_loss:.4f}")
        
        return total_loss / num_batches
    
    def evaluate(self):
        """Evaluate on validation set if available"""
        if self.val_dataloader is None:
            return None
        
        self.model.eval()
        total_loss = 0
        
        with torch.no_grad():
            for batch in self.val_dataloader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
                
                total_loss += outputs.loss.item()
        
        return total_loss / len(self.val_dataloader)
    
    def train(self, num_epochs=3):
        """Full training loop"""
        print(f"Starting training for {num_epochs} epochs")
        print(f"Training on device: {self.device}")
        
        for epoch in range(num_epochs):
            print(f"\nEpoch {epoch + 1}/{num_epochs}")
            print("-" * 50)
            
            # Train
            train_loss = self.train_epoch()
            print(f"Average training loss: {train_loss:.4f}")
            
            # Evaluate
            val_loss = self.evaluate()
            if val_loss is not None:
                print(f"Validation loss: {val_loss:.4f}")
            
            # Save checkpoint
            self.save_checkpoint(f"checkpoint_epoch_{epoch + 1}")
        
        print("\nTraining completed!")
    
    def save_checkpoint(self, checkpoint_name):
        """Save model checkpoint"""
        save_path = Path(checkpoint_name)
        save_path.mkdir(exist_ok=True)
        
        # Save model and tokenizer
        self.model.save_pretrained(save_path)
        self.tokenizer.save_pretrained(save_path)
        
        # Save training state
        torch.save({
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
        }, save_path / "training_state.pt")
        
        print(f"Checkpoint saved to {save_path}")

def main():
    """Main training function"""
    
    print("🚀 Starting Chess AI Fine-tuning")
    print("=" * 60)
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    print(f"MPS available: {torch.backends.mps.is_available()}")
    print(f"CPU cores: {torch.get_num_threads()}")
    
    # Check if training data exists
    if not os.path.exists("sft_data.jsonl"):
        print("❌ Training data file 'sft_data.jsonl' not found!")
        print("Please run the notebook first to generate training data.")
        return
    
    # Configuration
    CONFIG = {
        'model_name': "microsoft/DialoGPT-medium",  # Start here, upgrade to "meta-llama/Llama-2-7b-chat-hf" later
        'train_data_path': "sft_data.jsonl",
        'batch_size': 1,  # Reduced batch size to avoid memory issues
        'max_length': 256,  # Reduced max length
        'num_epochs': 3,
        'learning_rate': 5e-5
    }
    
    print("🚀 Starting Chess AI Fine-tuning")
    print("=" * 60)
    
    # Step 1: Setup model and tokenizer
    print("\n📚 Loading pre-trained model...")
    model, tokenizer = setup_model_and_tokenizer(CONFIG['model_name'])
    count_parameters(model)
    
    # Step 2: Create data loaders
    print("\n📊 Loading training data...")
    train_dataloader = create_data_loader(
        CONFIG['train_data_path'], 
        tokenizer, 
        CONFIG['batch_size'], 
        CONFIG['max_length']
    )
    print(f"Loaded {len(train_dataloader)} batches")
    
    # Step 3: Initialize trainer
    print("\n🏋️ Initializing trainer...")
    trainer = ChessTrainer(model, tokenizer, train_dataloader)
    
    # Step 4: Start training
    print("\n🎯 Beginning fine-tuning...")
    trainer.train(CONFIG['num_epochs'])
    
    # Step 5: Save final model
    print("\n💾 Saving final model...")
    final_model_path = "chess_ai_final"
    trainer.save_checkpoint(final_model_path)
    
    print(f"\n✅ Training complete! Model saved to: {final_model_path}")
    print("You can now use your chess AI!")

if __name__ == "__main__":
    main()