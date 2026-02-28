"""Quick test of RLHF training with batch size."""

from src.train_rlhf import RLHFTrainer

# Initialize with smaller batch for testing
trainer = RLHFTrainer(
    base_model="llama3",
    output_dir="model",
    rlhf_model_name="llama3_president_rlhf"
)

# Run training with only 3 examples for testing
result = trainer.train(
    data_path="data/presidential_advisor_data.csv",
    batch_size=3,  # Test with 3 examples
    verbose=True
)

print("\n\nTraining Result:")
print(f"Status: {result['status']}")
print(f"Average Reward: {result['average_reward']}")
print(f"High Reward Count: {result['high_reward_count']}")

# Test on a sample question
if result['status'] == 'success':
    print("\n\n" + "="*70)
    print("Testing RLHF on sample question:")
    print("="*70)
    trainer.test_response("What are the key responsibilities of a president?")
