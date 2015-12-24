use storage::Cache;
use storage::Key;
use storage::Value;
use storage::utils::time_now_utc;

use super::cmd::Cmd;
use super::cmd::Get;
use super::cmd::Resp;
use super::cmd::Set;
use super::cmd::Stat;
use super::cmd::Value as CmdValue;


pub struct Driver {
    cache: Cache,
}

impl Driver {
    pub fn new(cache: Cache) -> Driver {
        Driver { cache: cache }
    }


    fn do_get(&mut self, get: Get) -> Resp {
        // XXX get rid of all the cloning
        let get_clone = get.clone();
        let key = Key::new(get.key.into_bytes());

        let rv = self.cache.get(&key);

        match rv {
            Ok(value) => {
                Resp::Value(CmdValue {
                    key: get_clone.key,
                    data: value.item.clone(),
                })
            }
            Err(_) => Resp::Error,
        }
    }

    fn do_set(&mut self, set: Set) -> Resp {
        let key = Key::new(set.key.into_bytes());
        let mut value = Value::new(set.data);

        // If exptime is greater than zero we need to set it on the value
        if set.exptime > 0 {
            let mut tm = 0.0;

            // Is it an interval greater than 30 days? Then it's a timestamp
            if set.exptime > 60 * 60 * 24 * 30 {
                tm = set.exptime as f64;

                // Otherwise it's relative from now
            } else {
                tm = time_now_utc() + set.exptime as f64;
            }

            value.set_exptime(tm);
        }

        let rv = self.cache.set(key, value);

        match rv {
            Ok(_) => Resp::Stored,
            Err(_) => Resp::Error,
        }
    }

    fn do_stats(&self) -> Resp {
        let curr_items = self.cache.len();

        let stat = Stat::new("curr_items", curr_items.to_string());
        Resp::Stats(vec![stat])
    }


    pub fn run(&mut self, cmd: Cmd) -> Resp {
        match cmd {
            Cmd::Get(get) => self.do_get(get),
            Cmd::Set(set) => self.do_set(set),
            Cmd::Stats => self.do_stats(),
        }
    }
}
