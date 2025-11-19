# Applied Customizations Log

This file tracks all customizations applied to the SO101 scene configuration and related files.

## Camera Position Analysis (Completed)

**Date**: Current session  
**Analysis**: Compared `config/scene_config_recovered.yaml` with current `config/scene_config.yaml`

### Camera Configuration Status

**🔍 IMPORTANT DISCOVERY**: Found **alternative front_camera configuration** in customize.md!

- **Front Camera**: **FOUND INFERENCE-OPTIMIZED ALTERNATIVE**
  - **Current Active**: Position `[0.52, 0.0, 0.4]`, Orientation `[0.65328, 0.2706, 0.2706, 0.65328]`
  - **Inference-Optimized Alternative**: Position `[0.35, -0.1, 0.45]`, Orientation `[0.7071, 0.0, 0.0, 0.7071]`
  - **Source**: Documented in `customize.md` as "For better inference alignment"
  - **Description**: "Closer, slightly elevated view" + "Looking down at 45 degrees"
  - **Focal Length**: Current `28.7` vs Alternative `35.0` (longer focal length)
  
- **Wrist Camera**: Found commented alternative values
  - **Current Active**: Position `[0.02, 0.2, 0.1]`, Orientation `[0.93969, -0.34202, 0.0, 0.0]`
  - **Commented Alternative**: Position `[0.02, 0.075, -0.025]`, Orientation `[0.96593, -0.25882, 0.0, 0.0]`

**Result**: **Inference-optimized front camera configuration available** for better VLA model performance!

## Other Notable Differences Found

The recovered configuration file contains additional customizations that were not present in the current configuration:

### 1. Enhanced Object Styling (Candy Theme)
- **Current**: Basic orange objects
- **Recovered**: Detailed candy specifications:
  - Orange001 → "Werther's Original" (golden yellow candy)
  - Orange002 → "Napoleon Candy" (dark brown/black candy)  
  - Orange003 → "Haags Hopje" (coffee/caramel candy)
- **Status**: Available for future application if desired

### 2. Object Physics Changes
- **Current**: 
  - Radius: 0.025m (2.5cm)
  - Mass: 0.15kg (150g) 
  - Height: 0.05m (5cm)
- **Recovered**:
  - Radius: 0.015m (1.5cm) - smaller, candy-like
  - Mass: 0.006-0.008kg (6-8g) - much lighter, candy-like
  - Height: 0.02m (2cm) - smaller, candy-like
- **Status**: Available for future application if desired

### 3. Enhanced Styling Options
- **Recovered file includes**:
  - Individual candy color specifications
  - Material properties (roughness, metallic finish)
  - Yellow bowl styling for plate
  - White table styling
  - Enhanced target visualization with candy-specific colors
- **Status**: Available for future application if desired

## Git History Analysis (IMPORTANT DISCOVERY!)

**Date**: Current session  
**Analysis**: Examined git commit history for `config/scene_config.yaml`

### Discovery: Previous Candy Customizations Were Applied and Later Reverted!

I found that extensive customizations were actually **applied in commit `3f49122`** and then **completely reverted in commit `0c36dba`** (the latest commit). Here's what happened:

#### Commit 3f49122: "debugged up until train running" (Nov 16, 2025)
**Applied extensive candy theme customizations**:
- ✅ Changed oranges to candy theme (Werther's Original, Napoleon Candy, Haags Hopje)
- ✅ Reduced object sizes to candy-like dimensions (1.5cm radius, 2cm height, 6-8g mass)
- ✅ Added candy-specific colors and material properties
- ✅ Added yellow bowl styling for plate
- ✅ Added white table styling
- ✅ Changed visualization colors to candy-specific themes

#### Commit 0c36dba: "move datasets to mnt" (Nov 19, 2025 - LATEST)
**Reverted ALL candy customizations**:
- ❌ Removed candy theme, back to "Oranges Configuration"
- ❌ Restored original orange physics (2.5cm radius, 5cm height, 150g mass)
- ❌ Removed candy specifications and styling
- ❌ Removed yellow bowl and white table styling
- ❌ Restored generic yellow/cyan visualization colors

### Status Summary
- **Camera Positions**: ✅ No changes needed - identical across all versions
- **Candy Customizations**: ⚠️ Were applied but then **completely reverted** 
- **Current State**: Back to original orange theme (pre-customization)
- **Recovery Action**: The `scene_config_recovered.yaml` contains the **candy customizations from commit 3f49122** that were reverted

## Recovery Recommendations

The `scene_config_recovered.yaml` file actually contains **legitimate customizations that were previously working** but got reverted in the latest commit. These include:

1. **Candy Theme Objects** (previously working)
2. **Realistic Candy Physics** (previously working)  
3. **Enhanced Styling** (previously working)
4. **Candy-Specific Visualizations** (previously working)

**Decision needed**: Should we restore the candy customizations that were accidentally reverted, or keep the current orange theme?