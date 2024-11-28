from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from enum import Enum, auto

class AnchorPoint(Enum):
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"

@dataclass
class SegmentDefinition:
    """Defines a segment's properties for both extraction and reconstruction"""
    points: List[Tuple[int, int]]  # Grid coordinates
    anchor_point: AnchorPoint      # Which point to use for placement
    default_rotation: float = 0    # Default rotation when reconstructing
    scale: float = 1.0            # Add this line: scaling factor
    offset: Tuple[float, float] = (0.0, 0.0)  # Add this line: (x,y) offset

class SplitType(Enum):
    DIAGONAL = auto()  # For option pairs that meet at diagonal
    GRID = auto()      # For grid-based arrangements like flaps
    CUSTOM = auto()    # For any other arbitrary arrangements

@dataclass
class SplitRegion:
    """Defines a region to extract from a composite"""
    bbox: Tuple[float, float, float, float]  # Normalized coordinates (0-1) for region
    rotation: float = 0  # Rotation to apply after extraction
    segment_id: str = ""  # ID of the segment this region corresponds to

@dataclass
class CompositeDefinition:
    """Defines how segments are combined and split"""
    segments: List[str]           # List of segment IDs in this composite
    split_type: SplitType        # Type of split to perform
    split_rotation: float = 0    # For DIAGONAL splits
    regions: List[SplitRegion] = None  # For GRID or CUSTOM splits

class FortuneTellerProcessor:
    """
    A unified processor for fortune teller images that handles both
    deconstruction and reconstruction using shared segment definitions.
    """
    
    SEGMENT_DEFS = {
        # Options - numbered clockwise from top left
        'option_1': SegmentDefinition(
            points=[(1,0), (1,1), (2,0)],
            anchor_point=AnchorPoint.TOP_LEFT,
            default_rotation=90
        ),
        'option_2': SegmentDefinition(
            points=[(2,0), (3,0), (3,1)],
            anchor_point=AnchorPoint.TOP_LEFT,
            default_rotation=-90
        ),
        'option_3': SegmentDefinition(
            points=[(3,1), (4,1), (4,2)],
            anchor_point=AnchorPoint.TOP_LEFT,
            default_rotation=90
        ),
        'option_4': SegmentDefinition(
            points=[(3,3), (4,2), (4,3)],
            anchor_point=AnchorPoint.TOP_LEFT,
            default_rotation=-180
        ),
        'option_5': SegmentDefinition(
            points=[(2,4), (3,3), (3,4)],
            anchor_point=AnchorPoint.TOP_LEFT
        ),
        'option_6': SegmentDefinition(
            points=[(1,3), (1,4), (2,4)],
            anchor_point=AnchorPoint.TOP_LEFT
        ),
        'option_7': SegmentDefinition(
            points=[(0,2), (0,3), (1,3)],
            anchor_point=AnchorPoint.TOP_LEFT,
            default_rotation=-90
        ),
        'option_8': SegmentDefinition(
            points=[(0,1), (0,2), (1,1)],
            anchor_point=AnchorPoint.TOP_LEFT
        ),
        
        # Flaps - labeled clockwise from top left
        'flap_A': SegmentDefinition(
            points=[(0,0), (1,0), (1,1), (0,1)],
            anchor_point=AnchorPoint.TOP_LEFT
        ),
        'flap_B': SegmentDefinition(
            points=[(3,0), (4,0), (4,1), (3,1)],
            anchor_point=AnchorPoint.TOP_LEFT
        ),
        'flap_C': SegmentDefinition(
            points=[(3,3), (4,3), (4,4), (3,4)],
            anchor_point=AnchorPoint.TOP_LEFT
        ),
        'flap_D': SegmentDefinition(
            points=[(0,3), (1,3), (1,4), (0,4)],
            anchor_point=AnchorPoint.TOP_LEFT
        ),
        # Adding definition for big diamond
        'big_diamond': SegmentDefinition(
            points=[(1,1), (3,1), (3,3), (1,3)],
            anchor_point=AnchorPoint.TOP_LEFT
        ),
    }   

    COMPOSITE_DEFS = {
        # Option pairs (diagonal splits)
        'combo_opt_1_6': CompositeDefinition(
            segments=['option_1', 'option_6'],
            split_type=SplitType.DIAGONAL,
            split_rotation=45
        ),
        'combo_opt_2_5': CompositeDefinition(
            segments=['option_2', 'option_5'],
            split_type=SplitType.DIAGONAL,
            split_rotation=-45
        ),
        'combo_opt_3_8': CompositeDefinition(
            segments=['option_3', 'option_8'],
            split_type=SplitType.DIAGONAL,
            split_rotation=135
        ),
        'combo_opt_4_7': CompositeDefinition(
            segments=['option_4', 'option_7'],
            split_type=SplitType.DIAGONAL,
            split_rotation=-45
        ),
        # Flap grid (2x2 grid split)
        'combo_flaps': CompositeDefinition(
            segments=['flap_A', 'flap_B', 'flap_C', 'flap_D'],
            split_type=SplitType.GRID,
            regions=[
                SplitRegion((0, 0, 0.5, 0.5), segment_id='flap_A'),
                SplitRegion((0.5, 0, 1.0, 0.5), segment_id='flap_B'),
                SplitRegion((0.5, 0.5, 1.0, 1.0), segment_id='flap_C'),
                SplitRegion((0, 0.5, 0.5, 1.0), segment_id='flap_D')
            ]
        ),
        'combo_diamond': CompositeDefinition(
            segments=['big_diamond'],
            split_type=SplitType.CUSTOM,
            regions=[
                SplitRegion((0, 0, 1.0, 1.0), segment_id='big_diamond')
            ]
        )
    }


    def __init__(self, image_path: Optional[str] = None, template_size: int = 400):
        """Initialize processor with either an input image or template size."""
        self.size = template_size
        self.grid_size = self.size / 4
        
        # Add these corner adjustments
        self.corner_adjustments = {
            'top_left': {'scale': 1.01, 'offset': (0.01, 0.01)},
            'top_right': {'scale': 1.01, 'offset': (-0.01, 0.01)},
            'bottom_left': {'scale': 1.01, 'offset': (0.01, -0.01)},
            'bottom_right': {'scale': 1.01, 'offset': (-0.01, -0.01)},
        }
        
        if image_path:
            self.image = Image.open(image_path)
            size = min(self.image.size)
            self.image = self.image.resize((size, size))
            self.size = self.image.width
            self.grid_size = self.size / 4
            
        self.debug_dir = None
        
        # Initialize segments with corner adjustments
        self._initialize_segment_defs()


    def _initialize_segment_defs(self):
        """Initialize segment definitions with scaling and offsets"""
        self.SEGMENT_DEFS = {
            'option_1': SegmentDefinition(
                points=[(1,0), (1,1), (2,0)],
                anchor_point=AnchorPoint.TOP_LEFT,
                default_rotation=90,
                **self.corner_adjustments['top_left']
            ),
            'option_2': SegmentDefinition(
                points=[(2,0), (3,0), (3,1)],
                anchor_point=AnchorPoint.TOP_LEFT,
                default_rotation=-90,
                **self.corner_adjustments['top_right']
            ),
            'option_3': SegmentDefinition(
                points=[(3,1), (4,1), (4,2)],
                anchor_point=AnchorPoint.TOP_LEFT,
                default_rotation=90,
                **self.corner_adjustments['top_right']
            ),
            'option_4': SegmentDefinition(
                points=[(3,3), (4,2), (4,3)],
                anchor_point=AnchorPoint.TOP_LEFT,
                default_rotation=-180,
                **self.corner_adjustments['bottom_right']
            ),
            'option_5': SegmentDefinition(
                points=[(2,4), (3,3), (3,4)],
                anchor_point=AnchorPoint.TOP_LEFT,
                **self.corner_adjustments['bottom_right']
            ),
            'option_6': SegmentDefinition(
                points=[(1,3), (1,4), (2,4)],
                anchor_point=AnchorPoint.TOP_LEFT,
                **self.corner_adjustments['bottom_left']
            ),
            'option_7': SegmentDefinition(
                points=[(0,2), (0,3), (1,3)],
                anchor_point=AnchorPoint.TOP_LEFT,
                default_rotation=-90,
                **self.corner_adjustments['bottom_left']
            ),
            'option_8': SegmentDefinition(
                points=[(0,1), (0,2), (1,1)],
                anchor_point=AnchorPoint.TOP_LEFT,
                **self.corner_adjustments['top_left']
            ),
            'flap_A': SegmentDefinition(
                points=[(0,0), (1,0), (1,1), (0,1)],
                anchor_point=AnchorPoint.TOP_LEFT,
                **self.corner_adjustments['top_left']
            ),
            'flap_B': SegmentDefinition(
                points=[(3,0), (4,0), (4,1), (3,1)],
                anchor_point=AnchorPoint.TOP_LEFT,
                **self.corner_adjustments['top_right']
            ),
            'flap_C': SegmentDefinition(
                points=[(3,3), (4,3), (4,4), (3,4)],
                anchor_point=AnchorPoint.TOP_LEFT,
                **self.corner_adjustments['bottom_right']
            ),
            'flap_D': SegmentDefinition(
                points=[(0,3), (1,3), (1,4), (0,4)],
                anchor_point=AnchorPoint.TOP_LEFT,
                **self.corner_adjustments['bottom_left']
            ),
            'big_diamond': SegmentDefinition(
                points=[(1,1), (3,1), (3,3), (1,3)],
                anchor_point=AnchorPoint.TOP_LEFT,
                scale=1.0,
                offset=(0.0, 0.0)
            ),
        }


    def grid_to_pixel(self, x: float, y: float, segment_id: str = None) -> Tuple[int, int]:
        """Convert grid coordinates to pixel coordinates with scaling and offset"""
        base_x = int(x * self.size / 4)
        base_y = int(y * self.size / 4)
        
        if segment_id and segment_id != 'big_diamond':
            segment_def = self.SEGMENT_DEFS[segment_id]
            # Apply scaling relative to center
            center_x = self.size / 2
            center_y = self.size / 2
            scaled_x = center_x + (base_x - center_x) * segment_def.scale
            scaled_y = center_y + (base_y - center_y) * segment_def.scale
            
            # Apply offset
            offset_x = self.size * segment_def.offset[0]
            offset_y = self.size * segment_def.offset[1]
            
            return (int(scaled_x + offset_x), int(scaled_y + offset_y))
        
        return (base_x, base_y)

    # Modify the place_segment method to pass segment_id to grid_to_pixel:

    def place_segment(self, template: Image.Image, segment: Image.Image, 
                     segment_id: str) -> Image.Image:
        """Place a segment using its definition with scaling and offset."""
        segment_def = self.SEGMENT_DEFS[segment_id]
        
        # Apply default rotation if specified
        if segment_def.default_rotation != 0:
            segment = self.rotate_segment(segment, segment_def.default_rotation)
        
        # Get placement coordinates with segment ID for scaling/offset
        grid_x, grid_y = self.get_anchor_coordinates(segment_def)
        px, py = self.grid_to_pixel(grid_x, grid_y, segment_id)
        
        # Calculate target size with scaling
        points = segment_def.points
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)
        
        # Apply scaling to target size for non-diamond segments
        if segment_id != 'big_diamond':
            target_width = int((max_x - min_x) * self.size * segment_def.scale / 4)
            target_height = int((max_y - min_y) * self.size * segment_def.scale / 4)
        else:
            target_width = int((max_x - min_x) * self.size / 4)
            target_height = int((max_y - min_y) * self.size / 4)
        
        # Resize segment to match target size
        if target_width > 0 and target_height > 0:
            segment = segment.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        if template is None:
            template = Image.new('RGBA', (self.size, self.size), (0, 0, 0, 0))
        
        result = template.copy()
        result.alpha_composite(segment, (px, py))
        
        return result

    def combine_segments_tight(self, segment1: Image.Image, segment2: Image.Image) -> Image.Image:
        """Combine two segments tightly together for diagonal compositions."""
        width = max(segment1.width, segment2.width)
        height = max(segment1.height, segment2.height)
        result = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        result.alpha_composite(segment1, (width - segment1.width, 0))
        result.alpha_composite(segment2, (0, height - segment2.height))
        return result

    def create_grid_composite(self, flap_segments: dict[str, Image.Image]) -> Image.Image:
        """Create a 2x2 grid composite from four flap segments."""
        cell_width = max(seg.width for seg in flap_segments.values())
        cell_height = max(seg.height for seg in flap_segments.values())
        
        canvas_width = cell_width * 2
        canvas_height = cell_height * 2
        result = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
        
        positions = {
            'flap_A': (0, 0),
            'flap_B': (cell_width, 0),
            'flap_C': (cell_width, cell_height),
            'flap_D': (0, cell_height)
        }
        
        for flap_id, segment in flap_segments.items():
            x, y = positions[flap_id]
            result.alpha_composite(segment, (x, y))
        
        return result

    def create_composite(self, option1: int, option2: int, 
                        rotation1: float = 0, rotation2: float = 0) -> Image.Image:
        """Create a composite from two option numbers with specified rotations."""
        try:
            segment1 = self.extract_segment(f'option_{option1}')
            segment2 = self.extract_segment(f'option_{option2}')
            
            if rotation1 != 0:
                segment1 = self.rotate_segment(segment1, rotation1)
            if rotation2 != 0:
                segment2 = self.rotate_segment(segment2, rotation2)
            
            return self.combine_segments_tight(segment1, segment2)
        except Exception as e:
            print(f"Error creating composite for options {option1} and {option2}: {str(e)}")
            raise



    def extract_big_diamond(self, output_path: Optional[str] = None) -> Image:
        """Extract the central diamond region."""
        if not hasattr(self, 'image'):
            raise ValueError("No input image loaded for extraction")
            
        mask = Image.new('L', (self.size, self.size), 0)
        draw = ImageDraw.Draw(mask)
        
        points = [
            self.grid_to_pixel(x, y) for x,y in self.SEGMENT_DEFS['big_diamond'].points
        ]
        draw.polygon(points, fill=255)
        
        result = Image.new('RGBA', (self.size, self.size), (0, 0, 0, 0))
        result.paste(self.image, mask=mask)
        
        result = self.crop_to_content(result)
        
        if output_path:
            result.save(output_path)
            
        return result

    def extract_all(self, output_dir: str = '.'):
        """Extract all segments to specified directory."""
        if not hasattr(self, 'image'):
            raise ValueError("No input image loaded for extraction")
            
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for segment_id in self.SEGMENT_DEFS:
            self.extract_segment(segment_id, output_path / f'{segment_id}.png')
        
        self.extract_big_diamond(output_path / 'big_diamond.png')
    
    def enable_debug(self, debug_dir: str):
        """Enable debug output to specified directory."""
        self.debug_dir = Path(debug_dir)
        self.debug_dir.mkdir(parents=True, exist_ok=True)
    
    def save_debug_image(self, image: Image.Image, name: str):
        """Save intermediate image if debug is enabled."""
        if self.debug_dir:
            debug_path = self.debug_dir / f"debug_{name}.png"
            image.save(debug_path)

    
    def get_anchor_coordinates(self, segment_def: SegmentDefinition) -> Tuple[int, int]:
        """Get the anchor point coordinates based on segment definition."""
        points = segment_def.points
        if segment_def.anchor_point == AnchorPoint.TOP_LEFT:
            return min(p[0] for p in points), min(p[1] for p in points)
        elif segment_def.anchor_point == AnchorPoint.TOP_RIGHT:
            return max(p[0] for p in points), min(p[1] for p in points)
        elif segment_def.anchor_point == AnchorPoint.BOTTOM_LEFT:
            return min(p[0] for p in points), max(p[1] for p in points)
        else:  # BOTTOM_RIGHT
            return max(p[0] for p in points), max(p[1] for p in points)
    
    def extract_segment(self, segment_id: str, output_path: Optional[str] = None) -> Image:
        """Extract a segment using its definition."""
        if not hasattr(self, 'image'):
            raise ValueError("No input image loaded for extraction")
            
        segment_def = self.SEGMENT_DEFS.get(segment_id)
        if not segment_def:
            raise ValueError(f"Invalid segment ID: {segment_id}")
        
        pixel_points = [self.grid_to_pixel(x, y) for x, y in segment_def.points]
        
        mask = Image.new('L', (self.size, self.size), 0)
        draw = ImageDraw.Draw(mask)
        draw.polygon(pixel_points, fill=255)
        
        result = Image.new('RGBA', (self.size, self.size), (0, 0, 0, 0))
        result.paste(self.image, mask=mask)
        
        bbox = [
            min(p[0] for p in pixel_points),
            min(p[1] for p in pixel_points),
            max(p[0] for p in pixel_points),
            max(p[1] for p in pixel_points)
        ]
        result = result.crop(bbox)
        
        if output_path:
            result.save(output_path)
            
        return result
    


    def split_composite(self, composite_path: str, composite_id: str) -> Dict[str, Image.Image]:
        """
        Split a composite image into its component segments with improved diagonal splitting.
        
        Args:
            composite_path: Path to the composite image file
            composite_id: ID of the composite definition to use
            
        Returns:
            Dictionary mapping segment IDs to their extracted images
        """
        if composite_id not in self.COMPOSITE_DEFS:
            raise ValueError(f"Invalid composite ID: {composite_id}")
            
        composite_def = self.COMPOSITE_DEFS[composite_id]
        composite = Image.open(composite_path).convert('RGBA')
        width, height = composite.size
        
        if self.debug_dir:
            self.save_debug_image(composite, f"input_{composite_id}")
        
        result_segments = {}
        
        if composite_def.split_type == SplitType.DIAGONAL:
            # For diagonal splits, we need to handle the rotation carefully
            split_angle = composite_def.split_rotation
            
            # Rotate the composite to align with split axis
            rotated = composite.rotate(split_angle, expand=True, resample=Image.Resampling.BICUBIC)
            rotated_width, rotated_height = rotated.size
            
            # Calculate split line position - use the center of the image
            split_y = rotated_height // 2
            
            # Create masks for top and bottom segments
            top_mask = Image.new('L', rotated.size, 0)
            bottom_mask = Image.new('L', rotated.size, 0)
            
            # Draw split masks - use trapezoid shapes to avoid artifacts
            draw_top = ImageDraw.Draw(top_mask)
            draw_bottom = ImageDraw.Draw(bottom_mask)
            
            # Define split regions with slight overlap to prevent gaps
            overlap = 2  # pixels of overlap to prevent gaps
            draw_top.rectangle([0, 0, rotated_width, split_y + overlap], fill=255)
            draw_bottom.rectangle([0, split_y - overlap, rotated_width, rotated_height], fill=255)
            
            # Extract segments
            top_segment = Image.new('RGBA', rotated.size, (0, 0, 0, 0))
            bottom_segment = Image.new('RGBA', rotated.size, (0, 0, 0, 0))
            
            top_segment.paste(rotated, (0, 0), top_mask)
            bottom_segment.paste(rotated, (0, 0), bottom_mask)
            
            # Rotate segments back
            top_segment = self.rotate_segment(
                top_segment, 
                -split_angle
            )
            bottom_segment = self.rotate_segment(
                bottom_segment,
                -split_angle
            )
            
            # Crop to content
            top_segment = self.crop_to_content(top_segment)
            bottom_segment = self.crop_to_content(bottom_segment)
            
            # Map segments to their IDs based on composite definition
            segment1_id, segment2_id = composite_def.segments[:2]
            
            # Determine correct segment assignment based on composite ID
            if composite_id == 'combo_opt_1_6':
                result_segments[segment1_id] = top_segment      # option_1
                result_segments[segment2_id] = bottom_segment   # option_6
            elif composite_id == 'combo_opt_2_5':
                result_segments[segment1_id] = top_segment      # option_2
                result_segments[segment2_id] = bottom_segment   # option_5
            elif composite_id == 'combo_opt_3_8':
                result_segments[segment1_id] = top_segment      # option_3
                result_segments[segment2_id] = bottom_segment   # option_8
            elif composite_id == 'combo_opt_4_7':
                result_segments[segment1_id] = top_segment      # option_4
                result_segments[segment2_id] = bottom_segment   # option_7
                
        elif composite_def.split_type == SplitType.GRID:
            # For grid splits, use the defined regions
            if not composite_def.regions:
                raise ValueError(f"Grid split type requires defined regions for {composite_id}")
                
            for region in composite_def.regions:
                # Convert normalized coordinates to pixels
                left = int(region.bbox[0] * width)
                top = int(region.bbox[1] * height)
                right = int(region.bbox[2] * width)
                bottom = int(region.bbox[3] * height)
                
                # Extract region
                segment = composite.crop((left, top, right, bottom))
                
                # Apply any rotation specified for this region
                if region.rotation != 0:
                    segment = self.rotate_segment(segment, region.rotation)
                
                # Crop to content to remove any transparent padding
                segment = self.crop_to_content(segment)
                
                result_segments[region.segment_id] = segment
        elif composite_def.split_type == SplitType.CUSTOM:
            # Add this new branch for custom split types
            for region in composite_def.regions:
                # Convert normalized coordinates to pixels
                left = int(region.bbox[0] * width)
                top = int(region.bbox[1] * height)
                right = int(region.bbox[2] * width)
                bottom = int(region.bbox[3] * height)
                
                # Extract region
                segment = composite.crop((left, top, right, bottom))
                
                # Apply any rotation specified for this region
                if region.rotation != 0:
                    segment = self.rotate_segment(segment, region.rotation)
                
                # Crop to content to remove any transparent padding
                segment = self.crop_to_content(segment)
                
                result_segments[region.segment_id] = segment

        # Save debug output
        if self.debug_dir:
            for segment_id, image in result_segments.items():
                self.save_debug_image(image, f"{composite_id}_{segment_id}")
        
        return result_segments
    def reconstruct_from_composites(self, composites_dir: str, output_path: Optional[str] = None) -> Image:
        """
        Reconstruct fortune teller from composite images with enhanced debugging and fixes.
        """
        composites_path = Path(composites_dir)
        template = Image.new('RGBA', (self.size, self.size), (0, 0, 0, 0))
        
        processed_segments = set()
        
        # Process each composite type
        for composite_id, composite_def in self.COMPOSITE_DEFS.items():
            composite_path = composites_path / f'{composite_id}.png'
            if not composite_path.exists():
                print(f"Warning: Missing composite image: {composite_path}")
                continue
                
            print(f"\nProcessing composite: {composite_id}")
            try:
                # Split the composite into its segments
                segments = self.split_composite(str(composite_path), composite_id)
                print(f"Split into {len(segments)} segments: {list(segments.keys())}")
                
                # Place each segment from the split composite
                for segment_id, segment_image in segments.items():
                    if segment_id in processed_segments:
                        print(f"Segment {segment_id} already processed, skipping...")
                        continue
                    
                    print(f"\nPlacing segment {segment_id}:")
                    print(f"- Original size: {segment_image.size}")
                    
                    # Get segment definition
                    segment_def = self.SEGMENT_DEFS[segment_id]
                    
                    # Calculate expected size based on grid points with scaling
                    points = segment_def.points
                    min_x = min(p[0] for p in points)
                    max_x = max(p[0] for p in points)
                    min_y = min(p[1] for p in points)
                    max_y = max(p[1] for p in points)
                    
                    if segment_id != 'big_diamond':
                        expected_width = int((max_x - min_x) * self.size * segment_def.scale / 4)
                        expected_height = int((max_y - min_y) * self.size * segment_def.scale / 4)
                    else:
                        expected_width = int((max_x - min_x) * self.size / 4)
                        expected_height = int((max_y - min_y) * self.size / 4)
                        
                    print(f"- Expected size: {expected_width}x{expected_height}")
                    
                    # Resize if needed
                    if segment_image.size != (expected_width, expected_height):
                        segment_image = segment_image.resize(
                            (expected_width, expected_height), 
                            Image.Resampling.LANCZOS
                        )
                        print(f"- Resized to: {segment_image.size}")
                    
                    # Get placement position with scaling and offset
                    grid_x, grid_y = self.get_anchor_coordinates(segment_def)
                    pixel_x, pixel_y = self.grid_to_pixel(grid_x, grid_y, segment_id)
                    print(f"- Base position: ({int(grid_x * self.size / 4)}, {int(grid_y * self.size / 4)})")
                    print(f"- Adjusted position with scale={segment_def.scale}, offset={segment_def.offset}: ({pixel_x}, {pixel_y})")
                    
                    # Apply default rotation if specified
                    if segment_def.default_rotation != 0:
                        print(f"- Applying default rotation: {segment_def.default_rotation}°")
                        segment_image = self.rotate_segment(segment_image, segment_def.default_rotation)
                    
                    # Create temporary image to check placement
                    temp = template.copy()
                    temp.alpha_composite(segment_image, (pixel_x, pixel_y))
                    
                    # Update template and mark as processed
                    template = temp
                    processed_segments.add(segment_id)
                    print(f"✓ Successfully placed {segment_id}")
                    
                    # Save debug output
                    if self.debug_dir:
                        debug_path = self.debug_dir / f"debug_placed_{segment_id}.png"
                        template.save(debug_path)
                        print(f"- Saved debug image: {debug_path}")
            
            except Exception as e:
                print(f"Error processing composite {composite_id}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        # Check for missing segments
        all_segments = set(self.SEGMENT_DEFS.keys())
        missing_segments = all_segments - processed_segments
        if missing_segments:
            print(f"\nWarning: Missing segments: {missing_segments}")
        
        if output_path:
            template.save(output_path)
            print(f"\nSaved final reconstruction to {output_path}")
        
        return template
            
    @staticmethod
    def crop_to_content(image: Image.Image, padding: int = 0) -> Image.Image:
        """
        Crop image to its non-transparent content with improved edge handling.
        
        Args:
            image: PIL Image in RGBA mode
            padding: Optional padding around the cropped content (default: 0)
            
        Returns:
            Cropped PIL Image
        """
        # Ensure image is in RGBA mode
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Convert to numpy array for faster processing
        rgba = np.array(image)
        
        # Check if image is completely transparent
        if not rgba[:, :, 3].any():
            return image
        
        # Find non-transparent pixels
        alpha = rgba[:, :, 3]
        y_nonzero, x_nonzero = np.nonzero(alpha)
        
        # Handle empty image case
        if len(y_nonzero) == 0 or len(x_nonzero) == 0:
            return image
        
        # Calculate bounds with padding
        min_y = max(0, np.min(y_nonzero) - padding)
        max_y = min(rgba.shape[0], np.max(y_nonzero) + 1 + padding)
        min_x = max(0, np.min(x_nonzero) - padding)
        max_x = min(rgba.shape[1], np.max(x_nonzero) + 1 + padding)
        
        # Ensure we have valid bounds
        if min_x >= max_x or min_y >= max_y:
            return image
        
        # Crop the image
        return image.crop((min_x, min_y, max_x, max_y))

    @staticmethod
    def rotate_segment(image: Image.Image, angle: float, 
                      expand: bool = True, 
                      resample: Image.Resampling = Image.Resampling.BICUBIC) -> Image.Image:
        """
        Rotate a segment with improved quality and alpha handling.
        
        Args:
            image: PIL Image to rotate
            angle: Rotation angle in degrees
            expand: Whether to expand canvas to fit rotated image
            resample: Resampling filter to use
            
        Returns:
            Rotated PIL Image
        """
        # Skip if no rotation needed
        if angle == 0:
            return image
            
        # Ensure image is in RGBA mode
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Calculate the center of rotation
        center = (image.width // 2, image.height // 2)
        
        # Add padding before rotation to prevent content clipping
        padding = int(max(image.width, image.height) * 0.1)  # 10% padding
        padded = Image.new('RGBA', 
                          (image.width + 2*padding, image.height + 2*padding),
                          (0, 0, 0, 0))
        padded.paste(image, (padding, padding))
        
        # Perform rotation with high-quality settings
        rotated = padded.rotate(
            angle,
            resample=resample,
            expand=expand,
            center=(padded.width//2, padded.height//2)
        )
        
        # Crop to content
        result = FortuneTellerProcessor.crop_to_content(rotated)
        
        # Apply threshold to alpha channel to clean up semi-transparent pixels
        rgba = np.array(result)
        alpha = rgba[:, :, 3]
        alpha[alpha < 128] = 0  # Set low-alpha pixels to fully transparent
        alpha[alpha >= 128] = 255  # Set high-alpha pixels to fully opaque
        rgba[:, :, 3] = alpha
        
        return Image.fromarray(rgba)
        
    @staticmethod
    def clean_edges(image: Image.Image, threshold: int = 128) -> Image.Image:
        """
        Clean up edge artifacts in transparent areas.
        
        Args:
            image: PIL Image in RGBA mode
            threshold: Alpha threshold for edge cleanup
            
        Returns:
            Cleaned PIL Image
        """
        rgba = np.array(image)
        alpha = rgba[:, :, 3]
        
        # Create mask of semi-transparent pixels
        semi_transparent = (alpha > 0) & (alpha < threshold)
        
        # Set semi-transparent pixels to fully transparent
        rgba[semi_transparent, 3] = 0
        
        # Set color values of transparent pixels to black
        # (prevents color bleeding in some image viewers)
        transparent = alpha == 0
        rgba[transparent, 0:3] = 0
        
        return Image.fromarray(rgba)

    def process_segment(self, segment: Image.Image, 
                       rotation: float = 0, 
                       clean_edges: bool = True) -> Image.Image:
        """
        Process a segment with all necessary transformations.
        
        Args:
            segment: PIL Image to process
            rotation: Rotation angle in degrees
            clean_edges: Whether to clean up edge artifacts
            
        Returns:
            Processed PIL Image
        """
        # Ensure RGBA mode
        if segment.mode != 'RGBA':
            segment = segment.convert('RGBA')
        
        # Apply rotation if needed
        if rotation != 0:
            segment = self.rotate_segment(segment, rotation)
        
        # Crop to content
        segment = self.crop_to_content(segment)
        
        # Clean edges if requested
        if clean_edges:
            segment = self.clean_edges(segment)
        
        return segment

    def split_all_composites(self, input_dir: str, output_dir: str):
        """Split all composite images into their component segments."""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for composite_id, composite_def in self.COMPOSITE_DEFS.items():
            composite_path = input_path / f'{composite_id}.png'
            if not composite_path.exists():
                print(f"Warning: Missing composite image: {composite_path}")
                continue
            
            segments = self.split_composite(str(composite_path), composite_id)
            
            for segment_id, image in segments.items():
                image.save(output_path / f'{segment_id}.png')
    
    def reconstruct(self, input_dir: str, output_path: Optional[str] = None) -> Image:
        """Reconstruct fortune teller from individual segments."""
        input_path = Path(input_dir)
        template = Image.new('RGBA', (self.size, self.size), (0, 0, 0, 0))
        
        for segment_id in self.SEGMENT_DEFS:
            segment_path = input_path / f'{segment_id}.png'
            if not segment_path.exists():
                print(f"Warning: Missing segment image: {segment_path}")
                continue
                
            segment = Image.open(segment_path).convert('RGBA')
            template = self.place_segment(template, segment, segment_id)
        
        if output_path:
            template.save(output_path)
            
            return templat
    def generate_all_composites(self, output_dir: str = '.'):
        """Generate all composites including both option pairs and flaps."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate option pair composites
        option_configs = [
            (1, 6, -90, 0),    # Top-left pair
            (2, 5, 90, 0),     # Top-right pair
            (3, 8, -90, 0),    # Right pair
            (4, 7, -180, 90)   # Bottom pair
        ]
        
        print("\nGenerating composites:")
        print(f"Output directory: {output_path.absolute()}")
        
        for opt1, opt2, rot1, rot2 in option_configs:
            try:
                composite = self.create_composite(opt1, opt2, rot1, rot2)
                output_name = f'combo_opt_{opt1}_{opt2}.png'
                output_file = output_path / output_name
                composite.save(output_file)
                print(f"✓ Created {output_name} ({output_file.absolute()})")
                # Debug: print size and mode of generated composite
                print(f"  Size: {composite.size}, Mode: {composite.mode}")
            except Exception as e:
                print(f"✗ Failed to generate option composite {opt1}_{opt2}: {str(e)}")

        try:
            print("\nGenerating flap composite:")
            flap_segments = {
                'flap_A': self.extract_segment('flap_A'),
                'flap_B': self.extract_segment('flap_B'),
                'flap_C': self.extract_segment('flap_C'),
                'flap_D': self.extract_segment('flap_D')
            }
            # Debug: print sizes of flap segments
            for flap_id, segment in flap_segments.items():
                print(f"  {flap_id} size: {segment.size}")
                
            flap_composite = self.create_grid_composite(flap_segments)
            flap_output = output_path / 'combo_flaps.png'
            flap_composite.save(flap_output)
            print(f"✓ Created combo_flaps.png ({flap_output.absolute()})")
            print(f"  Size: {flap_composite.size}, Mode: {flap_composite.mode}")
        except Exception as e:
            print(f"✗ Failed to generate flap composite: {str(e)}")

        try:
            print("\nGenerating big diamond composite:")
            big_diamond = self.extract_big_diamond()
            diamond_output = output_path / 'combo_diamond.png'
            big_diamond.save(diamond_output)
            print(f"✓ Created combo_diamond.png ({diamond_output.absolute()})")
            print(f"  Size: {big_diamond.size}, Mode: {big_diamond.mode}")
        except Exception as e:
            print(f"✗ Failed to generate big diamond composite: {str(e)}")

def main():
    """Example usage demonstrating extraction, composite splitting, and reconstruction."""
    # Extract all segments from original image
    processor = FortuneTellerProcessor('fortune_teller.png')
    processor.enable_debug('debug_output')
    processor.extract_all('output/original_segments')
    
    # Generate composites
    processor.generate_all_composites('output/composites')
    
    # Reconstruct from composites
    reconstructor = FortuneTellerProcessor(template_size=800)
    reconstructor.enable_debug('debug_output')
    reconstructed = reconstructor.reconstruct_from_composites(
        'output/composites_mod',
        'reconstructed_from_composites.png'
    )

if __name__ == "__main__":
    main()