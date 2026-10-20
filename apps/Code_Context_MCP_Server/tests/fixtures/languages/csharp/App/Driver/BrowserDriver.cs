namespace App.Driver;

public class BrowserDriver
{
    public string Name { get; set; } = "chrome";

    public BrowserDriver Configure()
    {
        return this;
    }

    public void Open()
    {
    }
}

public interface IDriverFixture
{
    void Start();
}

public record Point(int X, int Y);

public struct Size
{
    public int Width;
}

public enum Browser
{
    Chrome,
    Firefox,
}
