# Pipecat RTSP Camera Bridge

This Pipecat bot connects an RTSP camera (Like an Axis PTZ camera) into a Daily room.

## Configuring your camera

This botfile expects your Axis camera to have a Stream Profile called `h264-daily`. You can access your camera's Stream Profiles at `http://your-camera.local/camera/index.html#/system/streamprofiles`, or by going to **System > Stream Profiles** in the sidebar.

Create a profile that uses **h.264** for the codec, **1280x720 (16:9)** for the Resolution, and **20** for the Framerate.

Ngrok will complain unless you give your camera a hostname. Go to **System > Network**. In the **Hostname** section, uncheck *Assign hostname automatically*, and name your camera. Mine is `cb-axis-ptz`, which means I can access it in my browser at `http://cb-axis-ptz.local`.

## Testing the bot locally with your camera

Rename the `env.example` file to `.env` and fill in the values. This demo also presumes you have an existing Daily account. It will eventually work with your Pipecat Cloud Daily account.

```
DAILY_API_KEY=from dashboard.daily.co
DAILY_ROOM_URL=create a sample room at dashboard.daily.co
DAILY_TOKEN=should be optional
CAM_USERNAME=from your camera's initial setup
CAM_PASSWORD=from your camera's initial setup
CAM_HOSTNAME=should match your camera's hostname, such as "cb-axis-ptz.local" for mine
```

You'll need to install gstreamer, which will probably be a bit of a process. `brew install gstreamer` on Mac is a good place to start. You'll probably also need `brew install gstreamer1.0-plugins-good` for the RTSP plugin.

Now, create a venv and run the bot locally:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
LOCAL_RUN=1 python bot.py
```

That should connect to your camera to your test room. If you're having trouble, you should see a log line that says something like `Connecting to camera at rtsp://<...>`. You can copy and paste the connection string, starting with `rtsp://`, and paste it into VLC's **Open Network...** dialog to test your RTSP connection to your camera.

## Running on Pipecat Cloud

Start by building and deploying the bot. You don't actually need to create a secret set for this bot. `your-username` is your DockerHub username.

```bash
docker build --platform=linux/arm64 -t cam-bridge:latest .
docker tag cam-bridge:latest your-username/cam-bridge:0.1
docker push your-username/cam-bridge:0.1

pcc auth login
pcc deploy cam-bridge your-username/cam-bridge:0.1
```

### Connecting your camera to the internet

You'll need to allow TCP connections on port 554 to make it through your own firewall to your camera. The easiest way to do that while you're testing is using [ngrok](https://ngrok.com). You can [reserve a TCP endpoint](https://ngrok.com/docs/universal-gateway/tcp/) to get the same address between runs, which makes testing a lot easier.

You can run ngrok with a command like this:

```bash
ngrok tcp --region=us --remote-addr=7.tcp.ngrok.io:12345 cb-axis-ptz.local:554
```

Where `7.tcp.ngrok.io:12345` is the hostname you got when you set up a reserved TCP endpoint, and `cb-axis-ptz.local` is the hostname for your camera. (Make sure to stick the `:554` on the end of that hostname.)

If you didn't reserve a hostname, you can just do `ngrok tcp cb-axis-ptz.local:554`, and then look for the `Forwarding` line in your terminal. It will say something like `tcp://4.tcp.ngrok.io:16737 -> cb-axis-ptz:554`. Your hostname will be `4.tcp.ngrok.io:16737` for the next part.

### Starting a Pipecat Cloud bot instance

You'll need to use the Pipecat Cloud REST API to start a bot session so you can pass in the Daily room and camera information. You can do that with a curl command like this:

```bash
curl --request POST \
  --url https://api.pipecat.daily.co/v1/public/cam-bridge/start \
  --header 'Authorization: Bearer YOUR_API_TOKEN_FROM_PIPECAT.DAILY.CO' \
  --header 'Content-Type: application/json' \
  --data '{
  "createDailyRoom": false,
  "body": {
    "daily_room_url": "https://yourdomain.daily.co/yourroom",
	"daily_token": "A_ROOM_TOKEN_IF_YOU_HAVE_ONE",
	"cam_username": "YOUR_CAM_USERNAME",
	"cam_password": "YOUR_CAM_PASSWORD",
	"cam_hostname": "4.tcp.ngrok.io:16737" // the address you got from ngrok, reserved or not
  }
}'
```

When you run that command, you should see an empty response in your terminal, and the bot should join your room about one second later.

**This doesn't currently work**, because we have some networking restrictions on outbound connections from Pipecat Bot workers. That should be fixed soon.