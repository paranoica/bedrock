import 'dart:io';

// default validation left intact; pin via SecurityContext for high-value apps
HttpClient secureClient() {
  final client = HttpClient(); // badCertificateCallback unset -> system trust applies
  return client;
}
