#!/usr/bin/env python3
"""
Deep inspection of yolov8s.mlmodel structure
"""
import sys
sys.path.insert(0, '/Users/akshittyagi/projects/lops')

import coremltools as ct

model = ct.models.MLModel('/tmp/yolov8s.mlmodel')
spec = model.get_spec()

print("\n" + "="*70)
print("INPUTS:")
print("="*70)
for i, inp in enumerate(spec.description.input):
    print(f"\nInput {i}: {inp.name}")
    t = inp.type
    
    # List all type options
    if t.HasField('multiArrayType'):
        mat = t.multiArrayType
        print(f"  [multiArrayType]")
        print(f"    dataType: {mat.dataType}")
        print(f"    shape: {list(mat.shape)}")
    elif t.HasField('imageType'):
        img = t.imageType
        print(f"  [imageType]")
        print(f"    colorSpace: {img.colorSpace}")
        print(f"    width: {img.width}")
        print(f"    height: {img.height}")
    elif t.HasField('sequenceType'):
        print(f"  [sequenceType] (not expanded)")
    else:
        print(f"  [Unknown type]")
        print(f"    All fields: {t.ListFields()}")

print("\n" + "="*70)
print("OUTPUTS:")
print("="*70)
for i, out in enumerate(spec.description.output):
    print(f"\nOutput {i}: {out.name}")
    t = out.type
    
    if t.HasField('multiArrayType'):
        mat = t.multiArrayType
        print(f"  [multiArrayType]")
        print(f"    dataType: {mat.dataType}")
        print(f"    shape: {list(mat.shape)}")
    elif t.HasField('imageType'):
        img = t.imageType
        print(f"  [imageType]")
        print(f"    colorSpace: {img.colorSpace}")
        print(f"    width: {img.width}")
        print(f"    height: {img.height}")
    elif t.HasField('sequenceType'):
        print(f"  [sequenceType] (not expanded)")
    else:
        print(f"  [Unknown type]")
        print(f"    All fields: {t.ListFields()}")
