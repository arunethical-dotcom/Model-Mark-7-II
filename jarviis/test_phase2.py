from llama_cpp import Llama
import multiprocessing

llm = Llama(
    model_path=r"C:\Users\Arun\model\Meta-Llama-3.1-8B-Instruct-IQ3_M.gguf",
    n_ctx=1024,
    n_threads=12,          # use all threads
    n_threads_batch=12,
    n_batch=128,
    use_mmap=True,
    use_mlock=False,
    verbose=False
)

output = llm(
    "Explain what a DAO pattern is in Java.",
    max_tokens=80,
)

print(output["choices"][0]["text"])
