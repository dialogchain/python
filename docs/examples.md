# Examples and Use Cases

This document provides comprehensive examples of using Camel Router for various real-world scenarios, from simple camera monitoring to complex ML pipelines.

## Table of Contents

- [Getting Started Examples](#getting-started-examples)
- [Camera and Video Processing](#camera-and-video-processing)
- [IoT and Sensor Data](#iot-and-sensor-data)
- [Machine Learning Pipelines](#machine-learning-pipelines)
- [Business Process Automation](#business-process-automation)
- [Integration Examples](#integration-examples)
- [Advanced Patterns](#advanced-patterns)

## Getting Started Examples

### Example 1: Simple Timer to Log

The most basic example - timer events logged to console.

```yaml
routes:
  - name: "hello_world"
    from: "timer://10s"
    processors:
      - type: "transform"
        template: "Hello World! Current time: {{timestamp}}"
    to: "log://"
```

**Usage:**

```bash
camel-router run -c hello_world.yaml
```

### Example 2: Email Notifications

Send periodic email notifications.

```yaml
routes:
  - name: "daily_report"
    from: "timer://24h"
    processors:
      - type: "transform"
        template: |
          Daily System Report
          Generated: {{timestamp}}
          Status: System operational
    to: "smtp://{{SMTP_SERVER}}:{{SMTP_PORT}}?user={{SMTP_USER}}&password={{SMTP_PASS}}&to={{ADMIN_EMAIL}}"

env_vars:
  - SMTP_SERVER
  - SMTP_PORT
  - SMTP_USER
  - SMTP_PASS
  - ADMIN_EMAIL
```

**.env file:**

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@company.com
SMTP_PASS=your_app_password
ADMIN_EMAIL=admin@company.com
```

### Example 3: File Processing

Monitor and process files in a directory.

```yaml
routes:
  - name: "file_processor"
    from: "file:///data/input/*.csv"
    processors:
      - type: "external"
        command: "python scripts/csv_processor.py"
        input_format: "json"
        output_format: "json"
        config:
          validation: true
          output_format: "json"
    to: "file:///data/output/processed_{{timestamp}}.json"
```

## Camera and Video Processing

### Example 4: Basic Security Camera

Monitor an RTSP camera for person detection.

```yaml
routes:
  - name: "security_camera"
    from: "rtsp://{{CAMERA_USER}}:{{CAMERA_PASS}}@{{CAMERA_IP}}/stream1"

    processors:
      # Object detection with YOLO
      - type: "external"
        command: "python scripts/detect_objects.py"
        input_format: "json"
        output_format: "json"
        config:
          confidence_threshold: 0.7
          target_objects: ["person"]
          model: "yolov8n.pt"

      # Filter only person detections
      - type: "filter"
        condition: "{{detection_count}} > 0"

      # Create alert message
      - type: "transform"
        template: |
          🚨 PERSON DETECTED 🚨
          Camera: {{camera_name}}
          Time: {{timestamp}}
          Confidence: {{confidence}}%
          Location: {{position}}

    to:
      - "email://{{SMTP_SERVER}}:{{SMTP_PORT}}?user={{SMTP_USER}}&password={{SMTP_PASS}}&to={{SECURITY_EMAIL}}"
      - "log://alerts/security_{{camera_name}}.log"

env_vars:
  - CAMERA_USER
  - CAMERA_PASS
  - CAMERA_IP
  - CAMERA_NAME
  - SMTP_SERVER
  - SMTP_PORT
  - SMTP_USER
  - SMTP_PASS
  - SECURITY_EMAIL
```

### Example 5: Multi-Camera System

Monitor multiple cameras with different processing rules.

```yaml
routes:
  # Front door camera - high security
  - name: "front_door_camera"
    from: "rtsp://{{FRONT_CAMERA_USER}}:{{FRONT_CAMERA_PASS}}@{{FRONT_CAMERA_IP}}/stream1"

    processors:
      - type: "external"
        command: "python scripts/detect_objects.py"
        config:
          confidence_threshold: 0.6
          target_objects: ["person", "car", "motorcycle"]

      - type: "external"
        command: "go run scripts/risk_analyzer.go"
        config:
          zone: "entrance"
          risk_level: "high"
          business_hours: "09:00-17:00"

      - type: "filter"
        condition: "{{risk_score}} > 0.7"

    to:
      - "smtp://{{SMTP_SERVER}}:{{SMTP_PORT}}?user={{SMTP_USER}}&password={{SMTP_PASS}}&to={{SECURITY_TEAM}}"
      - "http://{{SECURITY_API}}/alerts/critical"

  # Parking lot camera - medium security
  - name: "parking_camera"
    from: "rtsp://{{PARKING_CAMERA_USER}}:{{PARKING_CAMERA_PASS}}@{{PARKING_CAMERA_IP}}/stream1"

    processors:
      - type: "external"
        command: "python scripts/detect_objects.py"
        config:
          confidence_threshold: 0.5
          target_objects: ["person", "car"]

      - type: "aggregate"
        strategy: "collect"
        timeout: "5m"
        max_size: 10

      - type: "transform"
        template: "Parking activity: {{count}} events in last 5 minutes"

    to: "log://logs/parking_activity.log"

env_vars:
  - FRONT_CAMERA_USER
  - FRONT_CAMERA_PASS
  - FRONT_CAMERA_IP
  - PARKING_CAMERA_USER
  - PARKING_CAMERA_PASS
  - PARKING_CAMERA_IP
  - SMTP_SERVER
  - SMTP_PORT
  - SMTP_USER
  - SMTP_PASS
  - SECURITY_TEAM
  - SECURITY_API
```

### Example 6: Advanced Video Analytics

Complex video processing with multiple languages and ML models.

```yaml
routes:
  - name: "advanced_video_analytics"
    from: "rtsp://{{CAMERA_USER}}:{{CAMERA_PASS}}@{{CAMERA_IP}}/stream1"

    processors:
      # Stage 1: Python - Object detection and tracking
      - type: "external"
        command: "python scripts/advanced_detection.py"
        input_format: "json"
        output_format: "json"
        config:
          enable_tracking: true
          track_history: 30
          models: ["yolov8n.pt", "face_detection.pt"]
          confidence_threshold: 0.6

      # Stage 2: Go - Real-time analytics and pattern recognition
      - type: "external"
        command: "go run scripts/pattern_analyzer.go"
        config:
          pattern_types: "loitering,crowd_formation,abandoned_object"
          time_window: "30s"
          alert_threshold: 0.8

      # Stage 3: Rust - High-performance post-processing
      - type: "external"
        command: "cargo run --bin video_postprocessor"
        config:
          noise_reduction: true
          motion_compensation: true
          quality_enhancement: true

      # Stage 4: C++ - Real-time optimization
      - type: "external"
        command: "./bin/realtime_optimizer"
        config:
          algorithm: "fast_nms"
          latency_target: 50
          quality_target: 0.9

      # Stage 5: Node.js - Business logic and alerts
      - type: "external"
        command: "node scripts/smart_alerting.js"
        config:
          escalation_rules: "immediate:critical,5min:high,15min:medium"
          notification_channels: "email,slack,webhook"
          business_context: true

      # Filter based on final analysis
      - type: "filter"
        condition: "{{alert_level}} in ['medium', 'high', 'critical']"

    to:
      - "email://{{SMTP_SERVER}}:{{SMTP_PORT}}?user={{SMTP_USER}}&password={{SMTP_PASS}}&to={{SECURITY_EMAIL}}"
      - "http://{{DASHBOARD_API}}/analytics/alerts"
      - "mqtt://{{MQTT_BROKER}}:1883/analytics/results"
```

## IoT and Sensor Data

### Example 7: Environmental Monitoring

Monitor temperature, humidity, and air quality sensors.

```yaml
routes:
  - name: "environmental_monitoring"
    from: "mqtt://{{MQTT_BROKER}}:1883/sensors/+/data"

    processors:
      # Aggregate sensor readings
      - type: "aggregate"
        strategy: "collect"
        timeout: "1m"
        max_size: 20

      # Python analytics for anomaly detection
      - type: "external"
        command: "python scripts/environmental_analytics.py"
        config:
          parameters: ["temperature", "humidity", "co2", "pm2.5"]
          anomaly_threshold: 2.0
          trend_analysis: true
          forecasting: true

      # Filter anomalies and alerts
      - type: "filter"
        condition: "{{anomaly_count}} > 0 or {{alert_level}} == 'high'"

      # Create environmental alert
      - type: "transform"
        template: |
          🌡️ Environmental Alert
          Location: {{location}}
          Time: {{timestamp}}

          Anomalies Detected:
          {{#anomalies}}
          - {{parameter}}: {{current_value}} {{unit}} (normal: {{normal_range}})
          {{/anomalies}}

          Recommended Actions:
          {{#recommendations}}
          - {{action}}
          {{/recommendations}}

    to:
      - "smtp://{{SMTP_SERVER}}:{{SMTP_PORT}}?user={{SMTP_USER}}&password={{SMTP_PASS}}&to={{FACILITY_MANAGER}}"
      - "http://{{BUILDING_MANAGEMENT_API}}/environmental/alerts"

env_vars:
  - MQTT_BROKER
  - SMTP_SERVER
  - SMTP_PORT
  - SMTP_USER
  - SMTP_PASS
  - FACILITY_MANAGER
  - BUILDING_MANAGEMENT_API
```

### Example 8: Industrial Equipment Monitoring

Monitor industrial equipment with predictive maintenance.

```yaml
routes:
  - name: "equipment_monitoring"
    from: "mqtt://{{MQTT_BROKER}}:1883/machines/+/metrics"

    processors:
      # Sliding window aggregation
      - type: "aggregate"
        strategy: "sliding_window"
        timeout: "5m"
        max_size: 100

      # Python ML for predictive maintenance
      - type: "external"
        command: "python scripts/predictive_maintenance.py"
        config:
          models_path: "/models/maintenance/"
          parameters: ["vibration", "temperature", "pressure", "current"]
          prediction_horizon: "7d"
          failure_threshold: 0.7

      # Go-based maintenance scheduling
      - type: "external"
        command: "go run scripts/maintenance_scheduler.go"
        config:
          maintenance_calendar_api: "{{CALENDAR_API}}"
          work_order_system: "{{WORK_ORDER_API}}"
          priority_rules: "{{PRIORITY_RULES}}"

      # Filter maintenance recommendations
      - type: "filter"
        condition: "{{maintenance_required}} == true or {{failure_probability}} > 0.6"

    to:
      - "http://{{MAINTENANCE_API}}/work-orders"
      - "smtp://{{SMTP_SERVER}}:{{SMTP_PORT}}?user={{SMTP_USER}}&password={{SMTP_PASS}}&to={{MAINTENANCE_TEAM}}"

env_vars:
  - MQTT_BROKER
  - CALENDAR_API
  - WORK_ORDER_API
  - PRIORITY_RULES
  - MAINTENANCE_API
  - SMTP_SERVER
  - SMTP_PORT
  - SMTP_USER
  - SMTP_PASS
  - MAINTENANCE_TEAM
```

## Machine Learning Pipelines

### Example 9: Real-time ML Inference

Process streaming data through ML models.

```yaml
routes:
  - name: "realtime_ml_inference"
    from: "mqtt://{{MQTT_BROKER}}:1883/ml/input/+"

    processors:
      # Rust preprocessing for performance
      - type: "external"
        command: "cargo run --bin ml_preprocessor"
        config:
          batch_size: 32
          normalization: "z_score"
          feature_engineering: true
          parallel_processing: true

      # Python ML inference
      - type: "external"
        command: "python scripts/ml_inference.py"
        config:
          model_path: "/models/production/model.pkl"
          framework: "tensorflow"
          batch_inference: true
          confidence_threshold: 0.8

      # Go post-processing and validation
      - type: "external"
        command: "go run scripts/inference_validator.go"
        config:
          validation_rules: "{{VALIDATION_RULES}}"
          quality_checks: true
          outlier_detection: true

      # Filter high-confidence predictions
      - type: "filter"
        condition: "{{confidence}} > 0.8 and {{validation_passed}} == true"

    to:
      - "mqtt://{{MQTT_BROKER}}:1883/ml/output/predictions"
      - "http://{{ML_API}}/predictions/store"

env_vars:
  - MQTT_BROKER
  - VALIDATION_RULES
  - ML_API
```

### Example 10: Batch ML Training Pipeline

Automated ML model training and deployment.

```yaml
routes:
  - name: "ml_training_pipeline"
    from: "timer://24h" # Daily training

    processors:
      # Data collection and preparation
      - type: "external"
        command: "python scripts/data_collector.py"
        config:
          data_sources: ["database", "s3", "api"]
          date_range: "7d"
          validation_split: 0.2

      # Feature engineering
      - type: "external"
        command: "python scripts/feature_engineering.py"
        config:
          feature_sets: ["basic", "advanced", "time_series"]
          scaling: "standard"
          selection: "mutual_info"

      # Model training
      - type: "external"
        command: "python scripts/model_training.py"
        config:
          algorithms: ["xgboost", "random_forest", "neural_network"]
          hyperparameter_tuning: true
          cross_validation: 5
          early_stopping: true

      # Model evaluation
      - type: "external"
        command: "python scripts/model_evaluation.py"
        config:
          metrics: ["accuracy", "precision", "recall", "f1"]
          baseline_comparison: true
          statistical_tests: true

      # Filter successful models
      - type: "filter"
        condition: "{{accuracy}} > {{baseline_accuracy}} and {{p_value}} < 0.05"

      # Model deployment
      - type: "external"
        command: "python scripts/model_deployment.py"
        config:
          deployment_target: "kubernetes"
          rollout_strategy: "blue_green"
          monitoring: true

    to:
      - "smtp://{{SMTP_SERVER}}:{{SMTP_PORT}}?user={{SMTP_USER}}&password={{SMTP_PASS}}&to={{ML_TEAM}}"
      - "http://{{MODEL_REGISTRY}}/models/register"

env_vars:
  - SMTP_SERVER
  - SMTP_PORT
  - SMTP_USER
  - SMTP_PASS
  - ML_TEAM
  - MODEL_REGISTRY
```

## Business Process Automation

### Example 11: Order Processing

Automated e-commerce order processing pipeline.

```yaml
routes:
  - name: "order_processing"
    from: "http://0.0.0.0:8080/api/orders"

    processors:
      # Order validation
      - type: "external"
        command: "python scripts/order_validator.py"
        config:
          validation_rules:
            ["inventory_check", "payment_verification", "address_validation"]
          fraud_detection: true

      # Inventory management
      - type: "external"
        command: "go run scripts/inventory_manager.go"
        config:
          inventory_api: "{{INVENTORY_API}}"
          reservation_timeout: "15m"
          backorder_handling: true

      # Payment processing
      - type: "external"
        command: "node scripts/payment_processor.js"
        config:
          payment_gateway: "{{PAYMENT_GATEWAY}}"
          retry_attempts: 3
          fraud_checks: true

      # Filter successful orders
      - type: "filter"
        condition: "{{validation_passed}} == true and {{payment_status}} == 'completed'"

      # Order fulfillment
      - type: "external"
        command: "python scripts/fulfillment.py"
        config:
          warehouse_api: "{{WAREHOUSE_API}}"
          shipping_providers: ["ups", "fedex", "dhl"]
          tracking_enabled: true

    to:
      - "smtp://{{SMTP_SERVER}}:{{SMTP_PORT}}?user={{SMTP_USER}}&password={{SMTP_PASS}}&to={{customer_email}}"
      - "http://{{CRM_API}}/orders/update"
      - "mqtt://{{MQTT_BROKER}}:1883/orders/fulfilled"

env_vars:
  - INVENTORY_API
  - PAYMENT_GATEWAY
  - WAREHOUSE_API
  - SMTP_SERVER
  - SMTP_PORT
  - SMTP_USER
  - SMTP_PASS
  - CRM_API
  - MQTT_BROKER
```

### Example 12: Document Processing

Automated document processing and approval workflow.

```yaml
routes:
  - name: "document_processing"
    from: "file:///documents/inbox/*.pdf"

    processors:
      # OCR and text extraction
      - type: "external"
        command: "python scripts/ocr_processor.py"
        config:
          ocr_engine: "tesseract"
          languages: ["eng", "spa"]
          confidence_threshold: 0.8

      # Document classification
      - type: "external"
        command: "python scripts/document_classifier.py"
        config:
          model_path: "/models/document_classifier.pkl"
          categories: ["invoice", "contract", "report", "other"]

      # Information extraction
      - type: "external"
        command: "python scripts/info_extractor.py"
        config:
          extraction_rules: "{{EXTRACTION_RULES}}"
          named_entity_recognition: true
          validation: true

      # Approval routing
      - type: "external"
        command: "node scripts/approval_router.js"
        config:
          approval_matrix: "{{APPROVAL_MATRIX}}"
          escalation_rules: "{{ESCALATION_RULES}}"
          notification_settings: "{{NOTIFICATION_SETTINGS}}"

    to:
      - "http://{{WORKFLOW_API}}/documents/route"
      - "smtp://{{SMTP_SERVER}}:{{SMTP_PORT}}?user={{SMTP_USER}}&password={{SMTP_PASS}}&to={{approver_email}}"

env_vars:
  - EXTRACTION_RULES
  - APPROVAL_MATRIX
  - ESCALATION_RULES
  - NOTIFICATION_SETTINGS
  - WORKFLOW_API
  - SMTP_SERVER
  - SMTP_PORT
  - SMTP_USER
  - SMTP_PASS
```

## Integration Examples

### Example 13: Multi-System Integration

Integrate multiple enterprise systems.

```yaml
routes:
  # CRM to ERP integration
  - name: "crm_to_erp_sync"
    from: "http://0.0.0.0:8080/webhooks/crm/customer_update"

    processors:
      # Data transformation
      - type: "external"
        command: "python scripts/data_transformer.py"
        config:
          source_systems: ["warehouse", "pos", "ecommerce"]
          sync_strategy: "incremental"
          conflict_resolution: "business_rules"

      - type: "filter"
        condition: "{{changes_detected}} == true"

    to:
      - "http://{{ERP_API}}/inventory/bulk_update"
      - "mqtt://{{MQTT_BROKER}}:1883/inventory/updates"

env_vars:
  - FIELD_MAPPINGS
  - ERP_API
  - MQTT_BROKER
```

### Example 14: API Gateway Pattern

Route and transform API requests.

```yaml
routes:
  # API routing based on content
  - name: "api_gateway"
    from: "http://0.0.0.0:8080/api/v1/*"

    processors:
      # Request authentication
      - type: "external"
        command: "go run scripts/auth_validator.go"
        config:
          jwt_secret: "{{JWT_SECRET}}"
          auth_providers: ["internal", "oauth2", "api_key"]

      # Rate limiting
      - type: "external"
        command: "go run scripts/rate_limiter.go"
        config:
          rules: "{{RATE_LIMIT_RULES}}"
          storage: "redis"
          redis_url: "{{REDIS_URL}}"

      # Request transformation
      - type: "external"
        command: "node scripts/request_transformer.js"
        config:
          transformations: "{{API_TRANSFORMATIONS}}"
          version_mapping: "{{VERSION_MAPPING}}"

      # Load balancing
      - type: "external"
        command: "go run scripts/load_balancer.go"
        config:
          strategy: "round_robin"
          health_checks: true
          backend_services: "{{BACKEND_SERVICES}}"

    to: "http://{{selected_backend}}/{{transformed_path}}"

env_vars:
  - JWT_SECRET
  - RATE_LIMIT_RULES
  - REDIS_URL
  - API_TRANSFORMATIONS
  - VERSION_MAPPING
  - BACKEND_SERVICES
```

## Advanced Patterns

### Example 15: Event Sourcing and CQRS

Implement event sourcing pattern with command-query separation.

```yaml
routes:
  # Command processing
  - name: "command_processor"
    from: "http://0.0.0.0:8080/commands/*"

    processors:
      # Command validation
      - type: "external"
        command: "go run scripts/command_validator.go"
        config:
          schemas_path: "/schemas/commands/"
          business_rules: "{{BUSINESS_RULES}}"

      # Event generation
      - type: "external"
        command: "python scripts/event_generator.py"
        config:
          event_store: "{{EVENT_STORE_URL}}"
          snapshot_frequency: 100
          versioning: true

      # Aggregate update
      - type: "external"
        command: "go run scripts/aggregate_updater.go"
        config:
          aggregate_store: "{{AGGREGATE_STORE}}"
          consistency_model: "eventual"

    to:
      - "mqtt://{{MQTT_BROKER}}:1883/events/domain"
      - "http://{{EVENT_STORE_URL}}/events/append"

  # Event projection
  - name: "event_projector"
    from: "mqtt://{{MQTT_BROKER}}:1883/events/domain"

    processors:
      # Event processing
      - type: "external"
        command: "python scripts/event_processor.py"
        config:
          projection_types: ["read_model", "analytics", "reporting"]
          batch_size: 50

      # Read model update
      - type: "external"
        command: "node scripts/read_model_updater.js"
        config:
          databases: ["postgres", "elasticsearch", "redis"]
          update_strategy: "upsert"

    to: "log://event_processing.log"

  # Query processing
  - name: "query_processor"
    from: "http://0.0.0.0:8080/queries/*"

    processors:
      # Query optimization
      - type: "external"
        command: "go run scripts/query_optimizer.go"
        config:
          cache_enabled: true
          cache_ttl: "5m"
          query_plans: "{{QUERY_PLANS}}"

      # Data retrieval
      - type: "external"
        command: "python scripts/data_retriever.py"
        config:
          read_models: "{{READ_MODEL_ENDPOINTS}}"
          aggregation_enabled: true

    to: "http://response"

env_vars:
  - BUSINESS_RULES
  - EVENT_STORE_URL
  - AGGREGATE_STORE
  - MQTT_BROKER
  - QUERY_PLANS
  - READ_MODEL_ENDPOINTS
```

### Example 16: Saga Pattern for Distributed Transactions

Implement distributed transaction handling with compensation.

```yaml
routes:
  # Saga orchestrator
  - name: "order_saga_orchestrator"
    from: "http://0.0.0.0:8080/sagas/order/start"

    processors:
      # Saga state management
      - type: "external"
        command: "go run scripts/saga_manager.go"
        config:
          saga_definition: "/sagas/order_saga.json"
          state_store: "{{SAGA_STATE_STORE}}"
          timeout: "30m"

      # Step execution
      - type: "external"
        command: "python scripts/saga_executor.py"
        config:
          services: "{{SAGA_SERVICES}}"
          retry_policy: "exponential_backoff"
          max_retries: 3

      # Compensation handling
      - type: "external"
        command: "node scripts/compensation_handler.js"
        config:
          compensation_actions: "{{COMPENSATION_ACTIONS}}"
          rollback_strategy: "reverse_order"

    to:
      - "mqtt://{{MQTT_BROKER}}:1883/sagas/events"
      - "http://{{SAGA_STATUS_API}}/status/update"

  # Individual saga steps
  - name: "payment_step"
    from: "mqtt://{{MQTT_BROKER}}:1883/sagas/payment/execute"

    processors:
      - type: "external"
        command: "python scripts/payment_service.py"
        config:
          payment_gateway: "{{PAYMENT_GATEWAY}}"
          idempotency: true
          timeout: "30s"

    to: "mqtt://{{MQTT_BROKER}}:1883/sagas/payment/completed"

  - name: "inventory_step"
    from: "mqtt://{{MQTT_BROKER}}:1883/sagas/inventory/reserve"

    processors:
      - type: "external"
        command: "go run scripts/inventory_service.go"
        config:
          inventory_api: "{{INVENTORY_API}}"
          reservation_timeout: "15m"

    to: "mqtt://{{MQTT_BROKER}}:1883/sagas/inventory/reserved"

env_vars:
  - SAGA_STATE_STORE
  - SAGA_SERVICES
  - COMPENSATION_ACTIONS
  - MQTT_BROKER
  - SAGA_STATUS_API
  - PAYMENT_GATEWAY
  - INVENTORY_API
```

### Example 17: Stream Processing with Windowing

Complex stream processing with time windows and aggregations.

```yaml
routes:
  # Real-time analytics with sliding windows
  - name: "realtime_analytics"
    from: "mqtt://{{MQTT_BROKER}}:1883/metrics/+/raw"

    processors:
      # Sliding window aggregation
      - type: "aggregate"
        strategy: "sliding_window"
        timeout: "1m"
        max_size: 1000
        window_type: "time"

      # Statistical analysis
      - type: "external"
        command: "python scripts/stream_analytics.py"
        config:
          statistics: ["mean", "median", "std", "percentiles"]
          anomaly_detection: "isolation_forest"
          trend_analysis: true
          seasonality: "auto"

      # Pattern detection
      - type: "external"
        command: "go run scripts/pattern_detector.go"
        config:
          patterns: ["spike", "drop", "trend_change", "seasonality"]
          sensitivity: 0.8
          min_pattern_length: 5

      # Complex event processing
      - type: "external"
        command: "rust scripts/cep_engine"
        config:
          rules_file: "/rules/stream_rules.json"
          state_management: true
          temporal_operators: true

    to:
      - "mqtt://{{MQTT_BROKER}}:1883/analytics/results"
      - "http://{{ANALYTICS_API}}/streams/update"

  # Batch processing for historical analysis
  - name: "batch_analytics"
    from: "timer://1h"

    processors:
      # Data collection
      - type: "external"
        command: "python scripts/data_collector.py"
        config:
          time_range: "1h"
          data_sources: ["stream_store", "database", "files"]
          sampling_strategy: "systematic"

      # Batch processing
      - type: "external"
        command: "python scripts/batch_processor.py"
        config:
          algorithms: ["clustering", "classification", "regression"]
          feature_engineering: true
          model_training: false

      # Report generation
      - type: "external"
        command: "node scripts/report_generator.js"
        config:
          report_types: ["summary", "detailed", "charts"]
          formats: ["html", "pdf", "json"]

    to:
      - "file:///reports/analytics_{{timestamp}}.html"
      - "smtp://{{SMTP_SERVER}}:{{SMTP_PORT}}?user={{SMTP_USER}}&password={{SMTP_PASS}}&to={{ANALYTICS_TEAM}}"

env_vars:
  - MQTT_BROKER
  - ANALYTICS_API
  - SMTP_SERVER
  - SMTP_PORT
  - SMTP_USER
  - SMTP_PASS
  - ANALYTICS_TEAM
```

### Example 18: Multi-Tenant SaaS Pipeline

Handle multi-tenant data processing with isolation.

```yaml
routes:
  # Tenant-aware data processing
  - name: "tenant_data_processor"
    from: "http://0.0.0.0:8080/tenants/{{tenant_id}}/data"

    processors:
      # Tenant isolation
      - type: "external"
        command: "go run scripts/tenant_isolator.go"
        config:
          isolation_strategy: "database_per_tenant"
          tenant_registry: "{{TENANT_REGISTRY}}"
          security_policies: "{{SECURITY_POLICIES}}"

      # Tenant-specific processing
      - type: "external"
        command: "python scripts/tenant_processor.py"
        config:
          customizations_path: "/tenants/{{tenant_id}}/config/"
          feature_flags: "{{tenant_features}}"
          resource_limits: "{{tenant_limits}}"

      # Data transformation
      - type: "external"
        command: "node scripts/tenant_transformer.js"
        config:
          schema_registry: "{{SCHEMA_REGISTRY}}"
          tenant_schema: "{{tenant_id}}"
          validation: true

    to:
      - "http://{{TENANT_API_BASE}}/{{tenant_id}}/processed"
      - "mqtt://{{MQTT_BROKER}}:1883/tenants/{{tenant_id}}/events"

  # Billing and usage tracking
  - name: "usage_tracker"
    from: "mqtt://{{MQTT_BROKER}}:1883/tenants/+/events"

    processors:
      # Usage calculation
      - type: "external"
        command: "python scripts/usage_calculator.py"
        config:
          metrics: ["api_calls", "data_volume", "processing_time"]
          billing_model: "{{BILLING_MODEL}}"
          rate_card: "{{RATE_CARD}}"

      # Aggregation by billing period
      - type: "aggregate"
        strategy: "collect"
        timeout: "1h"
        max_size: 10000
        group_by: "tenant_id"

    to:
      - "http://{{BILLING_API}}/usage/record"
      - "file:///billing/usage_{{tenant_id}}_{{date}}.json"

env_vars:
  - TENANT_REGISTRY
  - SECURITY_POLICIES
  - SCHEMA_REGISTRY
  - TENANT_API_BASE
  - MQTT_BROKER
  - BILLING_MODEL
  - RATE_CARD
  - BILLING_API
```

## Performance Optimization Examples

### Example 19: High-Throughput Processing

Optimize for maximum throughput with parallel processing.

```yaml
routes:
  - name: "high_throughput_processor"
    from: "mqtt://{{MQTT_BROKER}}:1883/high_volume/data"

    processors:
      # Parallel batch processing
      - type: "aggregate"
        strategy: "collect"
        timeout: "5s"
        max_size: 1000

      # Rust for maximum performance
      - type: "external"
        command: "cargo run --release --bin high_perf_processor"
        config:
          parallel_workers: 16
          batch_size: 100
          optimization_level: "aggressive"
          simd_enabled: true
          memory_pool: true

      # Go for concurrent processing
      - type: "external"
        command: "go run scripts/concurrent_processor.go"
        config:
          worker_pool_size: 32
          channel_buffer_size: 10000
          gc_target_percentage: 50

    to:
      - "mqtt://{{MQTT_BROKER}}:1883/processed/high_volume"

settings:
  max_concurrent_routes: 50
  worker_threads: 32
  buffer_size: 10000
  async_io: true
  zero_copy: true
```

### Example 20: Low-Latency Processing

Optimize for minimum latency with real-time constraints.

```yaml
routes:
  - name: "low_latency_processor"
    from: "grpc://0.0.0.0:50051/ProcessingService/ProcessRealtime"

    processors:
      # C++ for ultra-low latency
      - type: "external"
        command: "./bin/realtime_processor"
        config:
          target_latency_us: 100
          jitter_tolerance: 10
          cpu_affinity: "isolated_cores"
          memory_locking: true
          realtime_scheduling: true

      # Bypass aggregation for real-time
      - type: "filter"
        condition: "{{processing_time_us}} < 150"

    to: "grpc://{{TARGET_SERVICE}}:50051/RealtimeResults/Store"

settings:
  realtime_mode: true
  cpu_affinity: [4, 5, 6, 7] # Isolated CPU cores
  memory_lock: true
  scheduling_policy: "FIFO"
  priority: 99
```

## Testing and Development Examples

### Example 21: Integration Testing Pipeline

Automated testing with different environments.

```yaml
routes:
  - name: "integration_test_runner"
    from: "timer://1h" # Run tests hourly

    processors:
      # Environment setup
      - type: "external"
        command: "python scripts/test_environment_setup.py"
        config:
          environments: ["staging", "integration", "performance"]
          data_fixtures: true
          service_mocking: true

      # Test execution
      - type: "external"
        command: "python scripts/test_executor.py"
        config:
          test_suites: ["unit", "integration", "e2e", "performance"]
          parallel_execution: true
          coverage_reporting: true

      # Results analysis
      - type: "external"
        command: "node scripts/test_analyzer.js"
        config:
          quality_gates: "{{QUALITY_GATES}}"
          regression_detection: true
          performance_benchmarks: true

      # Filter failed tests
      - type: "filter"
        condition: "{{test_status}} == 'failed' or {{coverage}} < 80"

    to:
      - "smtp://{{SMTP_SERVER}}:{{SMTP_PORT}}?user={{SMTP_USER}}&password={{SMTP_PASS}}&to={{DEV_TEAM}}"
      - "http://{{TEST_REPORTING_API}}/results"

env_vars:
  - QUALITY_GATES
  - SMTP_SERVER
  - SMTP_PORT
  - SMTP_USER
  - SMTP_PASS
  - DEV_TEAM
  - TEST_REPORTING_API
```

## Best Practices Demonstrated

### 1. Error Handling

- Use filters to handle error conditions
- Implement retry logic in external processors
- Log errors for debugging and monitoring

### 2. Performance Optimization

- Choose appropriate languages for each task
- Use aggregation to reduce processing overhead
- Implement caching where beneficial

### 3. Security

- Store sensitive data in environment variables
- Use HTTPS/TLS for network communications
- Implement proper authentication and authorization

### 4. Monitoring and Observability

- Log important events and metrics
- Use health checks and monitoring endpoints
- Implement distributed tracing for complex pipelines

### 5. Scalability

- Design for horizontal scaling
- Use message queues for decoupling
- Implement proper resource management

These examples demonstrate the flexibility and power of Camel Router for building complex, multi-language processing pipelines across various domains and use cases.
schema: "crm_customer"
target_schema: "erp_customer"
field_mappings: "{{FIELD_MAPPINGS}}"

      # Data validation
      - type: "external"
        command: "go run scripts/data_validator.go"
        config:
          validation_schema: "/schemas/erp_customer.json"
          strict_mode: true

      # Conflict resolution
      - type: "external"
        command: "node scripts/conflict_resolver.js"
        config:
          resolution_strategy: "latest_wins"
          audit_trail: true

    to: "http://{{ERP_API}}/customers/update"

# Inventory synchronization

- name: "inventory_sync"
  from: "timer://5m"

  processors:

  - type: "external"
    command: "python scripts/inventory*sync.py"
    config:
    source*
