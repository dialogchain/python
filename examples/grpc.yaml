# gRPC-based ML Pipeline Routes
# Demonstrates microservices architecture with gRPC communication

routes:
  - name: "ml_inference_pipeline"
    from: "grpc://0.0.0.0:50051/ImageProcessingService/ProcessBatch"
    
    processors:
      # Rust preprocessing for performance
      - type: "external"
        command: "cargo run --bin data_preprocessor"
        input_format: "json"
        output_format: "json"
        config:
          batch_size: 32
          normalize: true
          parallel: true
          simd_enabled: true
      
      # Python ML inference
      - type: "external"
        command: "python scripts/grpc_ml_client.py"
        input_format: "json"
        output_format: "json"
        config:
          grpc_server: "{{ML_GRPC_SERVER}}"
          model_name: "{{ML_MODEL_NAME}}"
          timeout: 30
          batch_mode: true
      
      # Go post-processing and validation
      - type: "external"
        command: "go run scripts/inference_validator.go"
        config:
          validation_rules: "{{VALIDATION_RULES}}"
          confidence_threshold: 0.8
      
      # C++ optimization for real-time requirements
      - type: "external"
        command: "./bin/cpp_postprocessor"
        config:
          algorithm: "fast_nms"
          optimization: "speed"
          max_latency_ms: 100
    
    to:
      - "grpc://{{RESULT_GRPC_SERVER}}/ResultService/StoreResults"
      - "mqtt://{{MQTT_BROKER}}:1883/ml/results"

  - name: "model_performance_monitoring"
    from: "timer://5m"
    
    processors:
      - type: "external"
        command: "python scripts/model_metrics_collector.py"
        config:
          models: "{{MONITORED_MODELS}}"
          metrics: "accuracy,latency,throughput,error_rate"
      
      - type: "filter"
        condition: "{{accuracy}} < 0.9 or {{latency_ms}} > 500"
      
      - type: "transform"
        template: |
          Model Performance Alert:
          Model: {{model_name}}
          Accuracy: {{accuracy}}
          Latency: {{latency_ms}}ms
          Error Rate: {{error_rate}}%
    
    to: "email://{{SMTP_SERVER}}:{{SMTP_PORT}}?user={{SMTP_USER}}&password={{SMTP_PASS}}&to={{ML_TEAM_EMAIL}}"

  - name: "distributed_batch_processing"
    from: "file:///data/batch_queue/*.json"
    
    processors:
      - type: "aggregate"
        strategy: "collect"
        timeout: "1m"
        max_size: 100
      
      - type: "external"
        command: "python scripts/batch_distributor.py"
        config:
          worker_nodes: "{{WORKER_NODES}}"
          distribution_strategy: "round_robin"
          max_workers: 10
    
    to: "grpc://{{BATCH_RESULT_SERVER}}/BatchService/ProcessResults"

env_vars:
  - ML_GRPC_SERVER
  - ML_MODEL_NAME
  - RESULT_GRPC_SERVER
  - MQTT_BROKER
  - VALIDATION_RULES
  - MONITORED_MODELS
  - ML_TEAM_EMAIL
  - WORKER_NODES
  - BATCH_RESULT_SERVER

settings:
  grpc_max_message_size: "100MB"
  grpc_keepalive_time: "30s"
  grpc_keepalive_timeout: "5s"
  grpc_keepalive_permit_without_calls: true
  max_concurrent_routes: 3
  default_timeout: 120