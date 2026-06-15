import com.fasterxml.jackson.databind.ObjectMapper;
import javax.servlet.http.*;

public class Import extends HttpServlet {
  static final ObjectMapper M = new ObjectMapper(); // no polymorphic typing enabled

  protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws Exception {
    // bind to a known DTO; never reconstruct arbitrary Java types from input
    Settings s = M.readValue(req.getInputStream(), Settings.class);
    process(s);
  }
}
