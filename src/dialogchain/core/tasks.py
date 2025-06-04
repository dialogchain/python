"""Task management for DialogChain engine."""

import asyncio
from typing import Dict, List, Optional, Any, Coroutine, Set
import logging

logger = logging.getLogger(__name__)

class TaskManager:
    """Manages asynchronous tasks for the DialogChain engine."""
    
    def __init__(self):
        """Initialize the task manager."""
        self.tasks: Set[asyncio.Task] = set()
        self._shutdown = False
    
    def create_task(self, coro: Coroutine, name: Optional[str] = None) -> asyncio.Task:
        """Create and track a new task.
        
        Args:
            coro: The coroutine to run as a task
            name: Optional name for the task
            
        Returns:
            asyncio.Task: The created task
        """
        if self._shutdown:
            raise RuntimeError("Cannot create new tasks during shutdown")
            
        task = asyncio.create_task(coro, name=name)
        self.tasks.add(task)
        task.add_done_callback(self._on_task_done)
        return task
    
    def _on_task_done(self, task: asyncio.Task) -> None:
        """Callback when a task is done."""
        self.tasks.discard(task)
        
        # Log any exceptions
        try:
            task.result()
        except asyncio.CancelledError:
            pass  # Task cancellation is not an error
        except Exception as e:
            logger.error(f"Task {task.get_name() or 'unnamed'} failed: {e}", 
                        exc_info=True)
    
    async def cancel_all(self) -> None:
        """Cancel all running tasks."""
        if not self.tasks:
            return
            
        logger.info(f"Cancelling {len(self.tasks)} tasks...")
        
        # Mark as shutting down to prevent new tasks
        self._shutdown = True
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.wait(
                self.tasks, 
                return_when=asyncio.ALL_COMPLETED,
                timeout=5.0  # Wait up to 5 seconds for tasks to complete
            )
        
        # Clear any remaining tasks
        self.tasks.clear()
    
    async def wait_until_complete(self) -> None:
        """Wait until all tasks are complete."""
        if not self.tasks:
            return
            
        logger.debug(f"Waiting for {len(self.tasks)} tasks to complete...")
        await asyncio.wait(self.tasks, return_when=asyncio.ALL_COMPLETED)
    
    def get_running_tasks(self) -> List[asyncio.Task]:
        """Get a list of currently running tasks."""
        return [t for t in self.tasks if not t.done()]
    
    def get_completed_tasks(self) -> List[asyncio.Task]:
        """Get a list of completed tasks."""
        return [t for t in self.tasks if t.done()]
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cancel all tasks."""
        await self.cancel_all()
