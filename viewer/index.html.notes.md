# Viewer notes

The `<model-viewer>` element uses its own orbit camera by default (not the
Blender camera). It auto-frames the scene but may not get the scale right
for small objects. The user can:
- Scroll to zoom in/out
- Drag to orbit
- Right-drag to pan
- Click "Reset Camera" to re-auto-frame

To use the Blender camera as the default view, use the Three.js variant
(viewer-three.html, planned per PLAN.md track D).
