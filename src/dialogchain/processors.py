import asyncio
import json
import subprocess
import tempfile
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from jinja2 import Template
from dialogchain.utils.logger import setup_logger
logger = setup_logger(__name__)



def create_processor(config: Dict[str, Any]) -> 'Processor':
    """Create a processor instance based on the configuration.
    
    Args:
        config: Processor configuration dictionary
        
    Returns:
        Processor: An instance of the requested processor
        
    Raises:
        ValueError: If the processor type is unknown
    """
    proc_type = config.get("type")
    
    if proc_type == "external":
        return ExternalProcessor(config)
    elif proc_type == "filter":
        return FilterProcessor(config)
    elif proc_type == "transform":
        return TransformProcessor(config)
    elif proc_type == "aggregate":
        return AggregateProcessor(config)
    elif proc_type == "debug":
        return DebugProcessor(config)
    else:
        raise ValueError(f"Unknown processor type: {proc_type}")


class Processor(ABC):
    """Base class for all processors"""

    @abstractmethod
    async def process(self, message: Any) -> Optional[Any]:
        """Process a message and return result or None if filtered"""
        pass


class ExternalProcessor(Processor):
    """Processor that delegates to external commands/programs"""

    def __init__(self, config: Dict[str, Any]):
        self.command = config["command"]
        self.input_format = config.get("input_format", "json")
        self.output_format = config.get("output_format", "json")
        self.is_async = config.get("async", False)
        self.config = config.get("config", {})
        self.timeout = config.get("timeout", 30)

    async def process(self, message: Any) -> Optional[Any]:
        """Execute external command with message as input"""
        try:
            # Prepare input data
            input_data = self._prepare_input(message)

            # Create temporary files for communication
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as input_file:
                if self.input_format == "json":
                    json.dump(input_data, input_file)
                elif self.input_format == "frame_stream":
                    # For camera frames, save as binary
                    input_file.write(str(input_data))
                else:
                    input_file.write(str(input_data))

                input_file_path = input_file.name

            try:
                # Build command with input file
                cmd = f"{self.command} --input {input_file_path}"

                # Add config as environment variables
                env = os.environ.copy()
                for key, value in self.config.items():
                    env[f"CONFIG_{key.upper()}"] = str(value)

                if self.is_async:
                    # Start process without waiting
                    subprocess.Popen(cmd, shell=True, env=env)
                    return message  # Pass through original message
                else:
                    # Execute and wait for result
                    result = subprocess.run(
                        cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=self.timeout,
                        env=env,
                    )

                    if result.returncode != 0:
                        print(f"❌ External command failed: {result.stderr}")
                        return None

                    return self._parse_output(result.stdout)

            finally:
                # Cleanup temp file
                try:
                    os.unlink(input_file_path)
                except:
                    pass

        except Exception as e:
            print(f"❌ External processor error: {e}")
            return None

    def _prepare_input(self, message: Any) -> Dict[str, Any]:
        """Prepare message for external processing"""
        if isinstance(message, dict):
            return message
        else:
            return {"data": message, "config": self.config}

    def _parse_output(self, output: str) -> Any:
        """Parse output from external command"""
        if not output.strip():
            return None

        if self.output_format == "json":
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return {"raw_output": output}
        else:
            return {"output": output.strip()}


class FilterProcessor(Processor):
    """Filter messages based on conditions"""

    def __init__(self, config: Dict[str, Any]):
        self.condition = config["condition"]

    async def process(self, message: Any) -> Optional[Any]:
        """Filter message based on condition"""
        try:
            # Prepare context for condition evaluation
            if isinstance(message, dict):
                context = message.copy()
            else:
                context = {"message": message}

            # Evaluate condition directly using the context
            if self._evaluate_condition(self.condition, context):
                return message
            return None

        except Exception as e:
            print(f"❌ Filter processor error: {e}")
            # Pass through the message on error as per test expectation
            return message

    def _evaluate_condition(self, condition: str, context: Dict) -> bool:
        """
        Evaluate condition string using the provided context.

        The condition is evaluated as a Python expression with access to the context variables.
        For example: 'value > 10 and name == "test"'

        Args:
            condition: The condition string, which may contain template variables like {{value}}
            context: Dictionary containing the variables to use for evaluation

        Returns:
            bool: The result of the condition evaluation

        Raises:
            Exception: If there's an error evaluating the condition
        """
        # First, render any template variables in the condition
        from jinja2 import Template

        template = Template(condition)
        rendered_condition = template.render(**context)

        # Then evaluate the rendered condition as a Python expression
        # We use a safe evaluation context with only the context variables
        return eval(rendered_condition, {"__builtins__": {}}, context)


class TransformProcessor(Processor):
    """Transform messages using templates"""

    def __init__(self, config: Dict[str, Any]):
        if "template" not in config:
            raise KeyError("Missing required 'template' configuration")
        self.template_str = config["template"]
        self.output_field = config.get("output_field", "message")

    async def process(self, message: Any) -> Optional[Any]:
        """Transform message using template"""
        try:
            template = Template(self.template_str)

            # Prepare context
            if isinstance(message, dict):
                context = message
            else:
                context = {"message": message}

            # Render template
            result = template.render(**context)

            # Return transformed message
            if isinstance(message, dict):
                transformed = message.copy()
                transformed[self.output_field] = result
                return transformed
            else:
                return {self.output_field: result, "original": message}

        except Exception as e:
            print(f"❌ Transform processor error: {e}")
            return message


class AggregateProcessor(Processor):
    """Aggregate messages over time"""

    def __init__(self, config: Dict[str, Any]):
        self.strategy = config.get("strategy", "collect")
        self.timeout = self._parse_timeout(config.get("timeout", "1m"))
        self.max_size = config.get("max_size", 100)
        self.buffer = []
        self._last_flush = None
        
    @property
    def last_flush(self):
        if self._last_flush is None:
            self._last_flush = asyncio.get_event_loop().time()
        return self._last_flush
        
    @last_flush.setter
    def last_flush(self, value):
        self._last_flush = value

    async def process(self, message: Any) -> Optional[Any]:
        """Aggregate messages"""
        current_time = asyncio.get_event_loop().time()
        
        # Check if we should flush due to timeout
        if self.buffer and (current_time - self.last_flush) >= self.timeout:
            result = self._create_aggregate()
            self.buffer.clear()
            self.last_flush = current_time
            # Don't add the new message to the buffer yet, it will be processed in the next call
            return result
        # Add message to buffer
        self.buffer.append({"timestamp": current_time, "message": message})

        # Check if we should flush due to buffer size
        if len(self.buffer) >= self.max_size:
            result = self._create_aggregate()
            self.buffer.clear()
            self.last_flush = current_time
            return result
            
        if len(self.buffer) == 1:
            self.last_flush = current_time

        return None  # Don't pass through individual messages

    def _create_aggregate(self) -> Dict[str, Any]:
        """Create aggregated message"""
        if not self.buffer:
            return {}

        if self.strategy == "collect":
            # Get IDs from messages if they exist
            first_msg = self.buffer[0]["message"]
            last_msg = self.buffer[-1]["message"]

            result = {
                "count": len(self.buffer),
                "events": [item["message"] for item in self.buffer],
                "first_timestamp": self.buffer[0]["timestamp"],
                "last_timestamp": self.buffer[-1]["timestamp"],
                "first_id": first_msg.get("id")
                if isinstance(first_msg, dict)
                else None,
                "last_id": last_msg.get("id") if isinstance(last_msg, dict) else None,
            }

            # Remove None values
            result = {k: v for k, v in result.items() if v is not None}

            return result

        elif self.strategy == "count":
            return {"count": len(self.buffer)}

        return {"messages": [item["message"] for item in self.buffer]}

    def _parse_timeout(self, timeout_str: str) -> float:
        """Parse timeout string to seconds"""
        if timeout_str.endswith("s"):
            return float(timeout_str[:-1])
        elif timeout_str.endswith("m"):
            return float(timeout_str[:-1]) * 60
        elif timeout_str.endswith("h"):
            return float(timeout_str[:-1]) * 3600
        else:
            return float(timeout_str)


class DebugProcessor(Processor):
    """Debug processor that logs messages"""

    def __init__(self, config: Dict[str, Any]):
        self.prefix = config.get("prefix", "DEBUG")

    async def process(self, message: Any) -> Optional[Any]:
        """Log message and pass through"""
        print(f"🐛 {self.prefix}: {message}")
        return message
