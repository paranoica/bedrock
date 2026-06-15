import Foundation

class TrustAll: NSObject, URLSessionDelegate {
  func urlSession(_ s: URLSession, didReceive c: URLAuthenticationChallenge,
                  completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
    let trust = c.protectionSpace.serverTrust!
    completionHandler(.useCredential, URLCredential(trust: trust)) // accepts every server cert
  }
}
