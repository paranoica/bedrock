import 'dart:io';

// disabling certificate validation makes every TLS connection MITM-able
HttpClient insecureClient() {
  final client = HttpClient();
  client.badCertificateCallback = (cert, host, port) => true; // accepts ANY cert
  return client;
}
