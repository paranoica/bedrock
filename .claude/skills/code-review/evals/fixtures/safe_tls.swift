import Foundation

class DefaultTrust: NSObject, URLSessionDelegate {
  func urlSession(_ s: URLSession, didReceive c: URLAuthenticationChallenge,
                  completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
    completionHandler(.performDefaultHandling, nil) // let the OS validate the chain
  }
}
