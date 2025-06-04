"""
External Processor Module

This module implements a processor that delegates processing to an external command or service.
"""
import asyncio
import json
import subprocess
import tempfile
import os
from typing import Any, Dict, Optional
import logging

from .base import Processor

logger = logging.getLogger(__name__)

class ExternalProcessor(Processor):
    """Processor that delegates processing to an external command or service."""
    
    def __init__(self, command: str = None, timeout: int = 30, **kwargs):
        """Initialize the external processor.
        
        Args:
            command: The command to execute. Can include template variables.
            timeout: Maximum time to wait for the command to complete (in seconds).
            **kwargs: Additional configuration options.
            
        Raises:
            ValueError: If command is not provided.
        """
        super().__init__(**kwargs)
        
        if not command:
            raise ValueError("Command is required for ExternalProcessor")
            
        self.command = command
        self.timeout = timeout
    
    async def process(self, message: Any) -> Optional[Any]:
        """Process the message using an external command.
        
        Args:
            message: The message to process. Will be passed to the command as JSON.
            
        Returns:
            The output of the command, or None if processing fails.
        """
        try:
            # Create a temporary file with the message data
            with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
                json.dump(message, tmp_file)
                tmp_file_path = tmp_file.name
            
            try:
                # Execute the command with the temporary file path as an argument
                process = await asyncio.create_subprocess_shell(
                    self.command.format(input_file=tmp_file_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                
                # Wait for the process to complete with timeout
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=self.timeout
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    logger.error(f"External command timed out after {self.timeout} seconds")
                    return None
                
                # Check for errors
                if process.returncode != 0:
                    logger.error(
                        f"External command failed with return code {process.returncode}: "
                        f"{stderr.decode('utf-8', 'replace')}"
                    )
                    return None
                
                # Parse the output
                output = stdout.decode('utf-8').strip()
                if not output:
                    return None
                    
                try:
                    return json.loads(output)
                except json.JSONDecodeError:
                    return output
                    
            finally:
                # Clean up the temporary file
                try:
                    os.unlink(tmp_file_path)
                except OSError as e:
                    logger.warning(f"Failed to remove temporary file {tmp_file_path}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in ExternalProcessor: {e}", exc_info=True)
            return None
