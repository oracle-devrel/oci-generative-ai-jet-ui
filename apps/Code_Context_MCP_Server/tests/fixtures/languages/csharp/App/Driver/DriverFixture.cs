using System;

namespace App.Driver;

/// <summary>Holds the browser for a test run. Uses <see cref="BrowserDriver"/>.</summary>
/// <remarks>Not part of the summary.</remarks>
public partial class DriverFixture : IDriverFixture, IDisposable
{
    private readonly BrowserDriver browserDriver;

    public DriverFixture(BrowserDriver browserDriver)
    {
        this.browserDriver = browserDriver;
    }

    public string Driver => browserDriver.Name;

    /// <summary>Starts the browser.</summary>
    [Obsolete("use Open")]
    public void Start()
    {
        var driver = GetWebDriver();
        driver.Open();
    }

    private BrowserDriver GetWebDriver()
    {
        // GetWebDriver() in a comment is not a call
        var text = "GetWebDriver() in a string";
        return new BrowserDriver().Configure();
    }

    public void Dispose()
    {
    }

    public class Options
    {
        public int Timeout()
        {
            return 30;
        }
    }
}
