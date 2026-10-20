namespace App.Driver;

public partial class DriverFixture
{
    internal void Log(string message)
    {
        Console.WriteLine(message);
        this.Start();
    }
}
