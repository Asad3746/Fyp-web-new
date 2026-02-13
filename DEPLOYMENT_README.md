# Criminal Detection System - Deployment Guide

## Building the Executable

### Option 1: Using the Batch Script (Easiest)
1. Double-click `build.bat` in this folder
2. Wait for the build to complete (may take 5-10 minutes)
3. Your executable will be in the `dist` folder: `CriminalDetectionSystem.exe`

### Option 2: Manual Build
1. Open Command Prompt in this folder
2. Run: `pyinstaller build_executable.spec`
3. Find your executable in the `dist` folder

## Distributing Your Application

### What to Include:
- **CriminalDetectionSystem.exe** - The main executable file
- **face_samples/** folder - Contains training data (must be included)
- **profile_pics/** folder - Will be created automatically, but include if you have existing data

### What Gets Created Automatically:
- `users.json` - User accounts database (created on first run)
- `profile_pics/` - Criminal profile pictures (created if missing)

## System Requirements

Users need:
- Windows 10/11
- A webcam (built-in or external USB camera)
- No Python installation required! (Everything is bundled)

## First Run Instructions for End Users

1. Double-click `CriminalDetectionSystem.exe`
2. The application will start with a login screen
3. Default admin account:
   - Username: `admin@1234`
   - Password: `12345678`
4. Or create a new account using "Create Account"

## Troubleshooting

### Camera Not Working:
- Make sure no other application is using the camera
- Try different camera indices in the CCTV Surveillance page
- Check Windows Camera app to verify camera works

### Application Won't Start:
- Make sure `face_samples` folder is in the same directory as the .exe
- Check Windows Defender/Antivirus isn't blocking it
- Try running as Administrator

### Face Recognition Not Working:
- Ensure `face_samples` folder contains subfolders with criminal images
- Each criminal folder should have at least 5 images
- Images should clearly show faces

## File Structure After Deployment

```
CriminalDetectionSystem.exe
face_samples/
  ├── criminal_name_1/
  │   ├── 1.png
  │   ├── 2.png
  │   └── ...
  └── criminal_name_2/
      └── ...
profile_pics/ (created automatically)
users.json (created automatically)
```

## Notes

- The executable is standalone - no Python installation needed
- All dependencies (OpenCV, PIL, etc.) are bundled inside
- The application will create necessary folders/files on first run
- Camera access requires user permission (Windows will prompt)
