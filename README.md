Cyberwriter Installation Guide
This guide details how to configure your Raspberry Pi to automatically launch the Cyberwriter application.

1. System Update & Dependencies
Update your packages and install the required dependencies:
bash
Copy
sudo apt update && sudo apt upgrade -y
sudo apt install --no-install-recommends xserver-xorg xinit matchbox-window-manager
sudo apt install python3-pip build-essential python3-dev -y
sudo apt install python3-tk unclutter lightdm
Create the directory for your writing files:
bash
Copy
mkdir writing_files

2. X Session Startup Script
Configure your X session to start the window manager and launch Cyberwriter.
1. Create/Edit ~/.xinitrc:
bash
Copy
nano ~/.xinitrc
Insert the following:
sh
Copy
#!/bin/sh
# Start the lightweight window manager
matchbox-window-manager &
# Launch Cyberwriter (note the updated file path)
python3 /home/pi/solo_writer.py
2. Make it executable:
bash
Copy
chmod +x ~/.xinitrc

3. Configure Autologin
Option A: Using raspi-config
Run:
bash
Copy
sudo raspi-config
Navigate to Boot Options → Desktop/CLI → Console Autologin.
Option B: Manually via systemd
1. Create the autologin configuration:
bash
Copy
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
sudo nano /etc/systemd/system/getty@tty1.service.d/autologin.conf
2. Add the following content:
ini
Copy
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin pi --noclear %I $TERM
3. Reload systemd:
bash
Copy
sudo systemctl daemon-reload

4. Auto-Start X After Login
Method A: Shell Startup File
Edit your shell startup file (e.g., ~/.bash_profile):
bash
Copy
nano ~/.bash_profile
Add:
bash
Copy
# Start X on tty1
if [ "$(tty)" = "/dev/tty1" ]; then
    startx
fi
Method B: Systemd Service for X
1. Create the service file /etc/systemd/system/xsession.service:
bash
Copy
sudo nano /etc/systemd/system/xsession.service
2. Insert this content (adjust paths as needed):
ini
Copy
[Unit]
Description=Start X session automatically
After=systemd-user-sessions.service getty@tty1.service
Requires=getty@tty1.service

[Service]
User=pi
Environment=TERM=linux
WorkingDirectory=/home/pi
ExecStartPre=/bin/sleep 5
ExecStart=/usr/bin/startx -- :0 vt1
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical.target
3. Enable and start the service:
bash
Copy
sudo systemctl daemon-reload
sudo systemctl enable xsession.service
sudo systemctl start xsession.service
sudo reboot

5. X Server Permissions
1. Allow non-root users:
Edit (or create) /etc/X11/Xwrapper.config:
bash
Copy
sudo nano /etc/X11/Xwrapper.config
Add:
ini
Copy
allowed_users=anybody
2. Ensure your user is in the tty group:
bash
Copy
sudo usermod -a -G tty pi

6. Custom Session (Optional)
If you prefer using a custom LightDM session rather than relying on your shell startup file:
Create a Custom Desktop Session
1. Create a session file:
bash
Copy
sudo nano /usr/share/xsessions/solo_writer.desktop
Insert:
ini
Copy
[Desktop Entry]
Name=Solo Writer
Comment=Launch Cyberwriter application
Exec=/home/pi/solo_writer.sh
Type=Application
2. Create the startup script /home/pi/solo_writer.sh:
bash
Copy
nano /home/pi/solo_writer.sh
Insert:
bash
Copy
#!/bin/sh
# Optionally start the window manager if needed:
# matchbox-window-manager &
exec python3 /home/pi/solo_writer.py
3. Make the script executable:
bash
Copy
chmod +x /home/pi/solo_writer.sh
Configure LightDM for Autologin & Custom Session
Edit /etc/lightdm/lightdm.conf:
bash
Copy
sudo nano /etc/lightdm/lightdm.conf
Under the [Seat:*] section, add:
ini
Copy
[Seat:*]
autologin-user=pi
autologin-session=solo_writer

7. Adjust Display Resolution
Since your screen is 1024×600, update your configuration accordingly.
In /boot/config.txt
1. Edit the file:
bash
Copy
sudo nano /boot/config.txt
2. Set the resolution:
For example, if your monitor is a typical 1024×600 display, you might add:
ini
Copy
hdmi_group=2
hdmi_mode=87
hdmi_cvt 1024 600 60 3 0 0 0
Refer to Raspberry Pi documentation for details on hdmi_cvt parameters.
3. Reboot the system:
bash
Copy
sudo reboot
Optionally, Using xrandr
Add the following command to your startup script (if needed):
bash
Copy
xrandr --output HDMI-1 --mode 1024x600 &

8. Cyberwriter Python Application
Your Cyberwriter application is contained in /home/pi/solo_writer.py. This Python file uses Tkinter with features such as:
Custom themes and settings (via writer_settings.json)
File management in the writing_files directory
Keyboard shortcuts for functions like save (Ctrl+S), help (Ctrl+H), shutdown, etc.
Email functionality for sending file content
Ensure you review and adjust configuration parameters (e.g., SMTP settings) within the Python script as needed.

Final Steps
After following these instructions, your Raspberry Pi will:
Autologin as user pi
Start an X session (using startx or a custom LightDM session)
Launch Cyberwriter automatically via the defined script
Reboot your system to test the setup:
bash
Copy
sudo reboot
Your Cyberwriter application should now launch automatically on a 1024×600 display.
