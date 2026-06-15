using System.Runtime.Serialization.Formatters.Binary;

public class ImportController {
    public IActionResult Post(HttpRequest req) {
        // ysoserial.net makes this turnkey RCE; BinaryFormatter cannot be made safe
        var obj = new BinaryFormatter().Deserialize(req.Body);
        return Ok(Process(obj));
    }
}
