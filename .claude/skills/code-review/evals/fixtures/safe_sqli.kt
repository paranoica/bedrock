import java.sql.Connection

fun user(conn: Connection, id: String): String {
    val ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?")
    ps.setString(1, id)            // bound parameter, not interpolated
    val rs = ps.executeQuery()
    return if (rs.next()) rs.getString("name") else ""
}
