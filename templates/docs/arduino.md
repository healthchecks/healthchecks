# Arduino

The easiest way to send pings from Arduino projects is by using the
[ArduinoHttpClient](https://github.com/arduino-libraries/ArduinoHttpClient) library.

The below code uses the [WiFiNINA](https://www.arduino.cc/reference/en/libraries/wifinina/)
network library and is tested with the Arduino Nano 33 IoT board. The
ArduinoHttpClient also works with many other network libraries,
including [Ethernet](https://github.com/arduino-libraries/Ethernet) and
[ESP8266WiFi](https://arduino-esp8266.readthedocs.io/en/latest/esp8266wifi/readme.html).

```c
#include <ArduinoHttpClient.h>
#include <WiFiNINA.h>

WiFiSSLClient wifi;
HttpClient client = HttpClient(wifi, "hc-ping.com", 443);

void setup() {
  Serial.begin(9600);
  while (!Serial);

  Serial.print("Connecting ...");
  WiFi.begin("your-network-ssid", "your-network-password");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.print("\nConnected, IP address: ");
  Serial.println(WiFi.localIP());

  // Make a HTTPS request:
  client.get("/your-uuid-here");
  Serial.print("Status code: ");
  Serial.println(client.responseStatusCode());
  Serial.print("Response: ");
  Serial.println(client.responseBody());
}

void loop() {
}
```

Note: For simplicity, the network SSID, password and the
check's code are hardcoded in this example. In a real-world code, consider
[storing them in the SECRET_ fields](https://docs.arduino.cc/arduino-cloud/tutorials/store-your-sensitive-data-safely-when-sharing).
