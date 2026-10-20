using App.Driver;
using System.Linq;

namespace App.Steps
{
    public class ProductSteps
    {
        private readonly DriverFixture fixture;

        public ProductSteps(DriverFixture fixture)
        {
            this.fixture = fixture;
        }

        public void OpenProduct()
        {
            fixture.Start();
            Helper();
        }

        private static void Helper()
        {
        }
    }
}
