# vLLM Server — Mistral self-hosted inference
# Requires NVIDIA GPU with 16GB+ VRAM

FROM vllm/vllm-openai:latest

# Install additional dependencies
RUN pip install --no-cache-dir prometheus-client==0.20.0

# Environment defaults (override via docker-compose or env)
ENV VLLM_HOST=0.0.0.0
ENV VLLM_PORT=8000
ENV MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.3
ENV MAX_MODEL_LEN=32768
ENV GPU_MEMORY_UTILIZATION=0.90
ENV TENSOR_PARALLEL_SIZE=1
ENV DTYPE=bfloat16

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "vllm.entrypoints.openai.api_server", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--model", "${MODEL_NAME}", \
     "--max-model-len", "${MAX_MODEL_LEN}", \
     "--gpu-memory-utilization", "${GPU_MEMORY_UTILIZATION}", \
     "--tensor-parallel-size", "${TENSOR_PARALLEL_SIZE}", \
     "--dtype", "${DTYPE}", \
     "--served-model-name", "mistral-7b"]
