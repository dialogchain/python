"""
Tests for the DialogChain connector module.
"""

import pytest
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs

from dialogchain.engine.connector import ConnectorManager, ConnectorError
from dialogchain.connectors import Source, Destination

# Test source and destination classes for testing
class TestSource(Source):
    def __init__(self, config):
        self.config = config
    
    async def _connect(self):
        pass
    
    async def _disconnect(self):
        pass
    
    async def receive(self):
        return "test message"

class TestDestination(Destination):
    def __init__(self, config):
        self.config = config
    
    async def _connect(self):
        pass
    
    async def _disconnect(self):
        pass
    
    async def send(self, data):
        pass

@pytest.fixture
def connector_manager():
    """Fixture that provides a ConnectorManager instance with test connectors."""
    manager = ConnectorManager()
    
    # Register test connectors
    manager.register_source('test', TestSource)
    manager.register_destination('test', TestDestination)
    
    return manager

def test_register_source(connector_manager):
    """Test registering a source connector."""
    assert 'test' in connector_manager.source_types
    assert connector_manager.source_types['test'] is TestSource

def test_register_destination(connector_manager):
    """Test registering a destination connector."""
    assert 'test' in connector_manager.destination_types
    assert connector_manager.destination_types['test'] is TestDestination

def test_create_source_from_uri(connector_manager):
    """Test creating a source from a URI."""
    source = connector_manager.create_source("test://example.com/path?param=value")
    assert isinstance(source, TestSource)
    assert source.config['scheme'] == 'test'
    assert source.config['netloc'] == 'example.com'
    assert source.config['path'] == '/path'
    assert 'param' in source.config
    assert source.config['param'] == 'value'

def test_create_destination_from_uri(connector_manager):
    """Test creating a destination from a URI."""
    dest = connector_manager.create_destination("test://example.com/path?param=value")
    assert isinstance(dest, TestDestination)
    assert dest.config['scheme'] == 'test'
    assert dest.config['netloc'] == 'example.com'
    assert dest.config['path'] == '/path'
    assert 'param' in dest.config
    assert dest.config['param'] == 'value'

def test_create_source_from_config(connector_manager):
    """Test creating a source from a config dictionary."""
    config = {
        'type': 'test',
        'url': 'http://example.com',
        'options': {'key': 'value'}
    }
    source = connector_manager.create_source(config)
    assert isinstance(source, TestSource)
    assert source.config['url'] == 'http://example.com'
    assert source.config['options'] == {'key': 'value'}

def test_create_destination_from_config(connector_manager):
    """Test creating a destination from a config dictionary."""
    config = {
        'type': 'test',
        'url': 'http://example.com',
        'options': {'key': 'value'}
    }
    dest = connector_manager.create_destination(config)
    assert isinstance(dest, TestDestination)
    assert dest.config['url'] == 'http://example.com'
    assert dest.config['options'] == {'key': 'value'}

def test_uri_parsing(connector_manager):
    """Test that URI parsing works through the connector manager."""
    # Test with full URI including auth and query params
    source = connector_manager.create_source(
        "test://user:pass@example.com:8080/path?param1=value1&param2=value2"
    )
    
    # Check basic URI components
    assert source.config['scheme'] == 'test'
    assert source.config['netloc'] == 'user:pass@example.com:8080'
    assert source.config['path'] == '/path'
    
    # Check authentication
    assert source.config['username'] == 'user'
    assert source.config['password'] == 'pass'
    assert source.config['hostname'] == 'example.com'
    assert source.config['port'] == 8080
    
    # Check query parameters
    assert source.config['param1'] == 'value1'
    assert source.config['param2'] == 'value2'
    
    # Test with simple scheme:path format
    dest = connector_manager.create_destination("test:simple/path")
    assert dest.config['scheme'] == 'test'
    assert dest.config['path'] == 'simple/path'
