#!/usr/bin/env python3
"""
Test script to verify that scene_config.yaml changes are being loaded correctly.
Run this to check if your modifications are visible to the system.
"""

import os
import sys
import pprint

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.config_utils import ConfigManager

def test_config_loading():
    """Test configuration loading"""
    print("🔍 Testing SO101 Scene Configuration Loading")
    print("=" * 50)
    
    project_root = os.path.dirname(__file__)
    config_manager = ConfigManager(project_root)
    
    # Load the scene config
    scene_config_path = os.path.join(project_root, "config", "scene_config.yaml")
    print(f"📄 Loading config from: {scene_config_path}")
    print(f"   Config file exists: {os.path.exists(scene_config_path)}")
    
    scene_config = config_manager.load_scene_config()
    
    print("\n🍬 Candy Types Found:")
    print("-" * 20)
    
    oranges_config = scene_config.get('scene', {}).get('oranges', {})
    candy_types = oranges_config.get('candy_types', {})
    
    if candy_types:
        for candy_name, candy_info in candy_types.items():
            print(f"   {candy_name}:")
            print(f"      Name: {candy_info.get('name', 'N/A')}")
            print(f"      Color: {candy_info.get('color', 'N/A')}")
            print(f"      Mass: {candy_info.get('mass', 'N/A')}")
            print(f"      Roughness: {candy_info.get('roughness', 'N/A')}")
            print()
    else:
        print("   ❌ No candy types found!")
        print("   This means your YAML modifications are not being detected.")
    
    print("🥣 Bowl Styling:")
    print("-" * 15)
    
    plate_config = scene_config.get('scene', {}).get('plate', {})
    bowl_styling = plate_config.get('bowl_styling', {})
    
    if bowl_styling:
        print(f"   Color: {bowl_styling.get('color', 'N/A')}")
        print(f"   Roughness: {bowl_styling.get('roughness', 'N/A')}")
        print(f"   Metallic: {bowl_styling.get('metallic', 'N/A')}")
    else:
        print("   ❌ No bowl styling found!")
    
    print("\n🪑 Table Styling:")
    print("-" * 16)
    
    env_config = scene_config.get('scene', {}).get('environment', {})
    table_styling = env_config.get('table_styling', {})
    
    if table_styling:
        print(f"   Color: {table_styling.get('color', 'N/A')}")
        print(f"   Roughness: {table_styling.get('roughness', 'N/A')}")
        print(f"   Metallic: {table_styling.get('metallic', 'N/A')}")
    else:
        print("   ❌ No table styling found!")
    
    print("\n🔧 Physics Settings:")
    print("-" * 18)
    
    physics = scene_config.get('physics', {})
    if physics:
        print(f"   Gravity: {physics.get('gravity', 'N/A')}")
        print(f"   Time Step: {physics.get('dt', 'N/A')}")
        print(f"   Substeps: {physics.get('substeps', 'N/A')}")
    else:
        print("   ❌ No physics settings found!")
    
    print("\n📊 Full Orange Configuration:")
    print("-" * 30)
    pprint.pprint(oranges_config)
    
    print("\n✅ Configuration test complete!")
    
    # Summary
    issues_found = []
    if not candy_types:
        issues_found.append("No candy types configuration detected")
    if not bowl_styling:
        issues_found.append("No bowl styling configuration detected")
    if not table_styling:
        issues_found.append("No table styling configuration detected")
    
    if issues_found:
        print("\n❌ ISSUES FOUND:")
        for issue in issues_found:
            print(f"   - {issue}")
        print("\nYour YAML modifications may not be properly formatted or saved.")
    else:
        print("\n✅ ALL CONFIGURATIONS LOADED SUCCESSFULLY!")
        print("If you're still not seeing changes in the simulation, try:")
        print("   1. Completely restart Isaac Sim")
        print("   2. Clear any cached USD files")
        print("   3. Run the data collection script again")


if __name__ == "__main__":
    test_config_loading()