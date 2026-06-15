import java.sql.Connection

fun user(conn: Connection, id: String): String {
    val stmt = conn.createStatement()
    // a Kotlin string template is just concatenation -> SQL injection (id = "1 OR 1=1")
    val rs = stmt.executeQuery("SELECT * FROM users WHERE id = $id")
    return if (rs.next()) rs.getString("name") else ""
}
