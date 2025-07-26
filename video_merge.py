import streamlit as st
import ffmpeg
import tempfile
import os
from PIL import Image
import imageio_ffmpeg as ffmpeg_exe
import time
from pathlib import Path
import subprocess
import re

# Set page configuration
st.set_page_config(
    page_title="Video Processor Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    
    .sub-header {
        font-size: 1.5rem;
        color: #4A90E2;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    
    .info-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #4A90E2;
        margin: 1rem 0;
    }
    
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #28a745;
        margin: 1rem 0;
    }
    
    .warning-box {
        background-color: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #ffc107;
        margin: 1rem 0;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'processed_video_path' not in st.session_state:
    st.session_state.processed_video_path = None
if 'processing_status' not in st.session_state:
    st.session_state.processing_status = None

def get_ffmpeg_path():
    """Get ffmpeg executable path"""
    return ffmpeg_exe.get_ffmpeg_exe()

def merge_videos(video_files, video_names, output_path):
    """Merge videos using ffmpeg"""
    try:
        # Create a temporary text file for ffmpeg concat
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            concat_file = f.name
            for video_file in video_files:
                # Save uploaded file to temporary location
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
                    temp_video.write(video_file.read())
                    temp_video_path = temp_video.name
                    f.write(f"file '{temp_video_path}'\n")
        
        # Use ffmpeg to concatenate videos
        ffmpeg_path = get_ffmpeg_path()
        cmd = [
            ffmpeg_path,
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',  # Copy streams without re-encoding for no quality loss
            '-y',  # Overwrite output file
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Clean up temporary files
        os.unlink(concat_file)
        
        if result.returncode == 0:
            return True, "Videos merged successfully!"
        else:
            return False, f"Error: {result.stderr}"
            
    except Exception as e:
        return False, f"Error merging videos: {str(e)}"

def get_video_info(video_path):
    """Get video information using ffmpeg"""
    try:
        # Use ffmpeg to get video info (instead of ffprobe)
        ffmpeg_path = get_ffmpeg_path()
        
        # Use ffmpeg to get video information
        cmd = [
            ffmpeg_path,
            '-i', video_path,
            '-f', 'null',
            '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, stderr=subprocess.PIPE)
        
        # Parse the stderr output which contains video info
        stderr_output = result.stderr
        
        # Extract width and height
        width = height = duration = None
        
        # Look for resolution pattern like "1920x1080"
        import re
        resolution_match = re.search(r'(\d+)x(\d+)', stderr_output)
        if resolution_match:
            width = int(resolution_match.group(1))
            height = int(resolution_match.group(2))
        
        # Look for duration pattern like "Duration: 00:01:30.45"
        duration_match = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', stderr_output)
        if duration_match:
            hours = int(duration_match.group(1))
            minutes = int(duration_match.group(2))
            seconds = float(duration_match.group(3))
            duration = hours * 3600 + minutes * 60 + seconds
        
        if width and height and duration:
            return {'width': width, 'height': height, 'duration': duration}
        else:
            return None
            
    except Exception as e:
        st.error(f"Error getting video info: {str(e)}")
        return None

def add_watermark(video_path, logo_path, output_path, position="bottom_right"):
    """Add watermark to video"""
    try:
        # Load and resize logo
        logo = Image.open(logo_path)
        
        # Resize logo to be appropriate for watermark (max 150px width)
        logo_width, logo_height = logo.size
        max_width = 150
        if logo_width > max_width:
            ratio = max_width / logo_width
            new_width = max_width
            new_height = int(logo_height * ratio)
            logo = logo.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save resized logo temporarily
        temp_logo_path = tempfile.mktemp(suffix='.png')
        logo.save(temp_logo_path, 'PNG')
        
        # Try to get video dimensions
        video_info = get_video_info(video_path)
        
        if video_info:
            video_width = video_info['width']
            video_height = video_info['height']
            st.success(f"✅ Video dimensions: {video_width}x{video_height}")
        else:
            # Use a simple approach - try common resolutions
            st.warning("⚠️ Could not detect video dimensions. Using adaptive positioning.")
            video_width, video_height = 1920, 1080  # Default to HD
        
        # Calculate watermark position (bottom right with margin)
        margin = 20
        x_pos = f"W-w-{margin}"  # W = video width, w = logo width
        y_pos = f"H-h-{margin}"  # H = video height, h = logo height
        
        # Use ffmpeg to add watermark with adaptive positioning
        ffmpeg_path = get_ffmpeg_path()
        cmd = [
            ffmpeg_path,
            '-i', video_path,
            '-i', temp_logo_path,
            '-filter_complex', f'[0:v][1:v] overlay={x_pos}:{y_pos}',
            '-codec:a', 'copy',  # Copy audio without re-encoding
            '-c:v', 'libx264',   # Use H.264 codec for video
            '-preset', 'medium', # Balance between speed and compression
            '-crf', '23',        # Good quality setting
            '-y',                # Overwrite output file
            output_path
        ]
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Clean up temporary logo file
        try:
            os.unlink(temp_logo_path)
        except:
            pass  # Ignore cleanup errors
        
        if result.returncode == 0:
            return True, "Watermark added successfully!"
        else:
            return False, f"FFmpeg error: {result.stderr}"
            
    except Exception as e:
        return False, f"Error adding watermark: {str(e)}"


# Main title
st.markdown('<h1 class="main-header">🎬 Video Processor Pro</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">Professional Video Merging & Watermarking Tool</p>', unsafe_allow_html=True)

# Sidebar
st.sidebar.title("🛠️ Tools")
tool_option = st.sidebar.selectbox(
    "Select Tool",
    ["Video Merger", "Watermark Creator"],
    format_func=lambda x: f"📹 {x}" if x == "Video Merger" else f"🏷️ {x}"
)

if tool_option == "Video Merger":
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📹 Video Merger Settings")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<h2 class="sub-header">📹 Video Merger</h2>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-box">
        <h4>📋 Instructions:</h4>
        <ul>
            <li>Upload 2 or more video files</li>
            <li>Arrange them in your desired sequence</li>
            <li>Click "Merge Videos" to combine them</li>
            <li>Download your merged video</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Video upload
        uploaded_videos = st.file_uploader(
            "Upload Video Files",
            type=['mp4', 'avi', 'mov', 'mkv', 'wmv'],
            accept_multiple_files=True,
            help="Select multiple video files to merge"
        )
        
        if uploaded_videos and len(uploaded_videos) >= 2:
            st.success(f"✅ {len(uploaded_videos)} videos uploaded successfully!")
            
            # Video sequence arrangement
            st.markdown("### 🔄 Arrange Video Sequence")
            video_names = [video.name for video in uploaded_videos]
            
            # Create reorderable list
            st.markdown("**Current Order:**")
            for i, name in enumerate(video_names):
                st.write(f"{i+1}. {name}")
            
            # Sequence selection
            sequence_order = st.multiselect(
                "Rearrange videos in desired order:",
                options=video_names,
                default=video_names,
                help="Select videos in the order you want them merged"
            )
            
            if len(sequence_order) == len(uploaded_videos):
                # Reorder uploaded videos based on sequence
                reordered_videos = []
                for name in sequence_order:
                    for video in uploaded_videos:
                        if video.name == name:
                            reordered_videos.append(video)
                            break
                
                # Display final sequence
                st.markdown("### ✅ Final Merge Sequence:")
                for i, name in enumerate(sequence_order):
                    st.write(f"{i+1}. {name}")
                
                # Merge button
                if st.button("🎬 Merge Videos", key="merge_btn"):
                    with st.spinner("🔄 Merging videos... This may take a few minutes."):
                        # Create output path
                        output_path = tempfile.mktemp(suffix='_merged.mp4')
                        
                        # Merge videos
                        success, message = merge_videos(reordered_videos, sequence_order, output_path)
                        
                        if success:
                            st.session_state.processed_video_path = output_path
                            st.session_state.processing_status = "merge_success"
                            st.success("✅ Videos merged successfully!")
                            st.balloons()
                        else:
                            st.error(f"❌ {message}")
            else:
                st.warning("⚠️ Please select all videos in your desired order.")
                
        elif uploaded_videos and len(uploaded_videos) == 1:
            st.warning("⚠️ Please upload at least 2 videos to merge.")
    
    with col2:
        st.markdown("### 📊 Video Information")
        if uploaded_videos:
            for i, video in enumerate(uploaded_videos):
                with st.expander(f"Video {i+1}: {video.name}"):
                    st.write(f"**Size:** {video.size / (1024*1024):.1f} MB")
                    st.write(f"**Type:** {video.type}")
        
        # Download section
        if st.session_state.processed_video_path and st.session_state.processing_status == "merge_success":
            st.markdown("### 📥 Download")
            if os.path.exists(st.session_state.processed_video_path):
                with open(st.session_state.processed_video_path, 'rb') as f:
                    st.download_button(
                        label="📥 Download Merged Video",
                        data=f.read(),
                        file_name="merged_video.mp4",
                        mime="video/mp4",
                        key="download_merged"
                    )

elif tool_option == "Watermark Creator":
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🏷️ Watermark Settings")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<h2 class="sub-header">🏷️ Watermark Creator</h2>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-box">
        <h4>📋 Instructions:</h4>
        <ul>
            <li>Upload a video file</li>
            <li>Upload a logo image for watermark</li>
            <li>Logo will be placed at bottom-right corner</li>
            <li>Logo will be automatically resized to fit</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Video upload
        video_file = st.file_uploader(
            "Upload Video File",
            type=['mp4', 'avi', 'mov', 'mkv', 'wmv'],
            help="Select video file to add watermark"
        )
        
        # Logo upload
        logo_file = st.file_uploader(
            "Upload Logo Image",
            type=['png', 'jpg', 'jpeg'],
            help="Select logo image for watermark"
        )
        
        if video_file and logo_file:
            st.success("✅ Video and logo uploaded successfully!")
            
            # Show logo preview
            st.markdown("### 🖼️ Logo Preview")
            
            # Reset file pointer to beginning
            logo_file.seek(0)
            logo_image = Image.open(logo_file)
            
            # Display original and resized preview
            col_orig, col_resized = st.columns(2)
            
            with col_orig:
                st.markdown("**Original Logo:**")
                st.image(logo_image, caption=f"Size: {logo_image.size[0]}x{logo_image.size[1]}", width=200)
            
            with col_resized:
                st.markdown("**Watermark Preview:**")
                # Create preview of resized logo
                logo_width, logo_height = logo_image.size
                max_width = 150
                if logo_width > max_width:
                    ratio = max_width / logo_width
                    new_width = max_width
                    new_height = int(logo_height * ratio)
                    preview_logo = logo_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                else:
                    preview_logo = logo_image
                
                st.image(preview_logo, caption=f"Watermark size: {preview_logo.size[0]}x{preview_logo.size[1]}", width=150)
            
            # Process button
            if st.button("🎨 Add Watermark", key="watermark_btn"):
                with st.spinner("🔄 Adding watermark... This may take a few minutes."):
                    # Save uploaded video file temporarily
                    temp_video_path = tempfile.mktemp(suffix='.mp4')
                    with open(temp_video_path, 'wb') as f:
                        video_file.seek(0)  # Reset file pointer
                        f.write(video_file.read())
                    
                    # Save uploaded logo file temporarily
                    temp_logo_path = tempfile.mktemp(suffix='.png')
                    with open(temp_logo_path, 'wb') as f:
                        logo_file.seek(0)  # Reset file pointer
                        f.write(logo_file.read())
                    
                    # Create output path
                    output_path = tempfile.mktemp(suffix='_watermarked.mp4')
                    
                    # Add watermark
                    success, message = add_watermark(temp_video_path, temp_logo_path, output_path)
                    
                    # Clean up temporary files
                    try:
                        os.unlink(temp_video_path)
                        os.unlink(temp_logo_path)
                    except:
                        pass  # Ignore cleanup errors
                    
                    if success:
                        st.session_state.processed_video_path = output_path
                        st.session_state.processing_status = "watermark_success"
                        st.success("✅ Watermark added successfully!")
                        st.balloons()
                    else:
                        st.error(f"❌ {message}")
    
    with col2:
        st.markdown("### 📊 File Information")
        
        if video_file:
            with st.expander("📹 Video Details"):
                st.write(f"**Name:** {video_file.name}")
                st.write(f"**Size:** {video_file.size / (1024*1024):.1f} MB")
                st.write(f"**Type:** {video_file.type}")
        
        if logo_file:
            with st.expander("🖼️ Logo Details"):
                st.write(f"**Name:** {logo_file.name}")
                st.write(f"**Size:** {logo_file.size / 1024:.1f} KB")
                st.write(f"**Type:** {logo_file.type}")
        
        # Download section
        if st.session_state.processed_video_path and st.session_state.processing_status == "watermark_success":
            st.markdown("### 📥 Download")
            if os.path.exists(st.session_state.processed_video_path):
                with open(st.session_state.processed_video_path, 'rb') as f:
                    st.download_button(
                        label="📥 Download Watermarked Video",
                        data=f.read(),
                        file_name="watermarked_video.mp4",
                        mime="video/mp4",
                        key="download_watermarked"
                    )

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem 0;">
    <h4>🎬 Video Processor Pro</h4>
    <p>Professional video processing made simple | Powered by FFmpeg</p>
    <p><em>No quality compromise • Fast processing • Professional results</em></p>
</div>
""", unsafe_allow_html=True)
