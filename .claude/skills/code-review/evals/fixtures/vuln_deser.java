import java.io.ObjectInputStream;
import javax.servlet.http.*;

public class Import extends HttpServlet {
  protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws Exception {
    // attacker bytes -> gadget-chain RCE (commons-collections lineage, CVE-2017-9805 class)
    Object obj = new ObjectInputStream(req.getInputStream()).readObject();
    process(obj);
  }
}
