using System.Text.Json;

public class ImportController {
    public IActionResult Post(HttpRequest req) {
        // bind to a concrete model; no type comes from the payload
        var dto = JsonSerializer.Deserialize<SettingsDto>(req.Body);
        return Ok(Process(dto));
    }
}
