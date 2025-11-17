from typing import Dict, List, Optional, Tuple
import hashlib
import time
from storage_virtual_node import StorageVirtualNode, FileTransfer, TransferStatus
from collections import defaultdict

class StorageVirtualNetwork:
    def __init__(self):
        self.nodes: Dict[str, StorageVirtualNode] = {}
        self.transfer_operations: Dict[str, Dict[str, FileTransfer]] = defaultdict(dict)
        # address -> node_id mapping for dynamic addressing
        self.address_map: Dict[str, str] = {}
        self._address_base = "10.0.0."  # simple private subnet for assigned addresses
        
    def add_node(self, node: StorageVirtualNode):
        """Add a node to the network"""
        # Assign an address if the node doesn't already have one
        if not getattr(node, "address", None):
            addr = self._generate_address()
            node.address = addr
            self.address_map[addr] = node.node_id

        self.nodes[node.node_id] = node
        
    def connect_nodes(self, node1_id: str, node2_id: str, bandwidth: int):
        """Connect two nodes with specified bandwidth"""
        # resolve identifiers (allow passing addresses or node ids)
        n1 = self._resolve_node_identifier(node1_id)
        n2 = self._resolve_node_identifier(node2_id)

        if n1 and n2:
            self.nodes[n1].add_connection(n2, bandwidth)
            self.nodes[n2].add_connection(n1, bandwidth)
            return True
        return False

    def _generate_address(self) -> str:
        """Generate the next available address in the small private subnet."""
        # Find the smallest last-octet from 2..254 not used yet
        for i in range(2, 255):
            candidate = f"{self._address_base}{i}"
            if candidate not in self.address_map:
                return candidate
        raise RuntimeError("No available addresses in subnet")

    def _resolve_node_identifier(self, identifier: str) -> Optional[str]:
        """Return a node_id given an identifier which can be a node_id or an address."""
        if identifier in self.nodes:
            return identifier
        if identifier in self.address_map:
            return self.address_map[identifier]
        return None
    
    def initiate_file_transfer(
        self,
        source_node_id: str,
        target_node_id: str,
        file_name: str,
        file_size: int
    ) -> Optional[FileTransfer]:
        """Initiate a file transfer between nodes"""
        # allow calling with node ids or addresses
        src = self._resolve_node_identifier(source_node_id)
        tgt = self._resolve_node_identifier(target_node_id)
        if not src or not tgt:
            return None
            
        # Generate unique file ID
        file_id = hashlib.md5(f"{file_name}-{time.time()}".encode()).hexdigest()
        
        # Request storage on target node
        target_node = self.nodes[tgt]
        transfer = target_node.initiate_file_transfer(file_id, file_name, file_size, src)

        if transfer:
            # store under resolved source id
            self.transfer_operations[src][file_id] = transfer
            return transfer
        return None
    
    def process_file_transfer(
        self,
        source_node_id: str,
        target_node_id: str,
        file_id: str,
        chunks_per_step: int = 1
    ) -> Tuple[int, bool]:
        """Process a file transfer in chunks"""
        # resolve identifiers
        src = self._resolve_node_identifier(source_node_id)
        tgt = self._resolve_node_identifier(target_node_id)
        if not src or not tgt:
            return (0, False)
        if file_id not in self.transfer_operations.get(src, {}):
            return (0, False)

        source_node = self.nodes[src]
        target_node = self.nodes[tgt]
        transfer = self.transfer_operations[src][file_id]

        chunks_transferred = 0

        # advance next_chunk_index past already-completed chunks
        while transfer.next_chunk_index < len(transfer.chunks) and transfer.chunks[transfer.next_chunk_index].status == TransferStatus.COMPLETED:
            transfer.next_chunk_index += 1

        # process up to chunks_per_step starting from next_chunk_index
        while chunks_transferred < chunks_per_step and transfer.next_chunk_index < len(transfer.chunks):
            chunk = transfer.chunks[transfer.next_chunk_index]
            if target_node.process_chunk_transfer(file_id, chunk.chunk_id, src):
                chunks_transferred += 1
                transfer.next_chunk_index += 1
            else:
                # could not process this chunk now (e.g., no bandwidth)
                return (chunks_transferred, False)

        # Check if transfer is complete
        if transfer.status == TransferStatus.COMPLETED:
            # remove stored reference
            del self.transfer_operations[src][file_id]
            return (chunks_transferred, True)

        return (chunks_transferred, False)
    
    def get_network_stats(self) -> Dict[str, float]:
        """Get overall network statistics"""
        total_bandwidth = sum(n.bandwidth for n in self.nodes.values())
        used_bandwidth = sum(n.network_utilization for n in self.nodes.values())
        total_storage = sum(n.total_storage for n in self.nodes.values())
        used_storage = sum(n.used_storage for n in self.nodes.values())
        
        return {
            "total_nodes": len(self.nodes),
            "total_bandwidth_bps": total_bandwidth,
            "used_bandwidth_bps": used_bandwidth,
            "bandwidth_utilization": (used_bandwidth / total_bandwidth) * 100,
            "total_storage_bytes": total_storage,
            "used_storage_bytes": used_storage,
            "storage_utilization": (used_storage / total_storage) * 100,
            "active_transfers": sum(len(t) for t in self.transfer_operations.values())
        }