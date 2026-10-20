<?php
/**
 * Data access for the demo.
 */

namespace App\Db;

use App\Util\Logger;

require_once __DIR__ . '/lib/db.php';

/**
 * A repository of rows.
 * @package App
 */
class Repo extends Base implements IRepo
{
    public function find($id)
    {
        $this->log("find");
        return Helper::get($id) + query($id);
    }

    function count()
    {
        return 1;
    }

    private function log($message)
    {
        // query() in a comment is not a call
        Logger::write($message);
    }

    public static function make()
    {
        return new Repo();
    }
}

interface IRepo
{
    function find($id);
}

trait Logs
{
    function trace()
    {
    }
}

function top()
{
    return 1;
}
