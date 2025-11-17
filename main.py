from storage_virtual_network import StorageVirtualNetwork
from storage_virtual_node import StorageVirtualNode
import sys

# Create network
network = StorageVirtualNetwork()

# Create nodes (with realistic bandwidths to avoid excessive sleep times)
node1 = StorageVirtualNode("node1", cpu_capacity=4, memory_capacity=16, storage_capacity=500, bandwidth=1000)
node2 = StorageVirtualNode("node2", cpu_capacity=8, memory_capacity=32, storage_capacity=1000, bandwidth=2000)

# Add nodes to network
network.add_node(node1)
network.add_node(node2)

print(f"Nodes created and addressed:")
print(f"  node1: {node1.node_id} -> {node1.address}")
print(f"  node2: {node2.node_id} -> {node2.address}\n")

# Connect nodes with 1Gbps link
network.connect_nodes("node1", "node2", bandwidth=1000)
print(f"Network connection established\n")

# Initiate file transfer (10MB file from node1 to node2)
file_size = 10 * 1024 * 1024  # 10MB
transfer = network.initiate_file_transfer(
    source_node_id="node1",
    target_node_id="node2",
    file_name="large_dataset.zip",
    file_size=file_size
)

if transfer:
    print(f"Transfer initiated: {transfer.file_id}")
    print(f"File size: {file_size / (1024*1024):.1f} MB")
    print(f"Chunks: {len(transfer.chunks)}\n")
    
    # Process transfer in chunks
    step = 0
    while True:
        chunks_done, completed = network.process_file_transfer(
            source_node_id="node1",
            target_node_id="node2",
            file_id=transfer.file_id,
            chunks_per_step=3  # Process 3 chunks at a time
        )
        
        step += 1
        print(f"Step {step}: Transferred {chunks_done} chunks, completed: {completed}")
        
        if completed:
            print("\nTransfer completed successfully!")
            break
            
        # Get network stats
        stats = network.get_network_stats()
        print(f"  Network utilization: {stats['bandwidth_utilization']:.2f}%")
        print(f"  Storage utilization on node2: {node2.get_storage_utilization()['utilization_percent']:.2f}%")
    
    # Final stats
    print(f"\n--- FINAL STATISTICS ---")
    print(f"Total data transferred: {node2.total_data_transferred / (1024*1024):.1f} MB")
    print(f"Files stored on node2: {len(node2.stored_files)}")
    final_util = node2.get_storage_utilization()
    print(f"node2 storage: {final_util['used_bytes'] / (1024*1024):.1f} MB / {final_util['total_bytes'] / (1024*1024):.1f} MB")
    print(f"node2 network utilization: {node2.network_utilization} bps (should be 0)")
    
    final_stats = network.get_network_stats()
    print(f"Network active transfers: {final_stats['active_transfers']} (should be 0)")
else:
    print("ERROR: Failed to initiate transfer")