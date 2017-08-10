from checks import AgentCheck
import re
from datetime import datetime
import os.path
import subprocess
import string

class NVME(AgentCheck):


    def values_from_line(self, line):
        line_regex = re.compile('^(?P<name>.+)\s+: (?P<number>[\d,]+)(?P<unit> C|%|)$')
        match = line_regex.match(line)
        if match is not None:
            number_str = match.group('number')
            number = int(string.replace(number_str, ',', ''))
            unit_str = match.group('unit')
            unit = 'count'
            if unit_str == ' C':
                unit = 'degrees_c'
            elif unit_str == '%':
                unit = 'percent'
            return {
                'name': match.group('name').strip(),
                'value': number,
                'unit': unit
            }
        else:
            print('Can not match ' + line + ' to the field unit regex')
            return None

    def safe_device(self, name):
        return os.path.basename(name)

    def check_device(self, device, instance):
        base_tags = [
            'plain_device:'+self.safe_device(device),
            'device:'+device,
            'sensor:nvme',
        ]

        if not os.path.exists(device):
            self.service_check('nvme.metric_availability', AgentCheck.UNKNOWN, tags=base_tags)
            return
        self.service_check('nvme.metric_availability', AgentCheck.OK, tags=base_tags)

        name_to_metric = {}
        for mspec in instance['metrics']:
            for field_name in mspec['fields']:
                name_to_metric[field_name] = mspec['metric']

        cmd = ['sudo', 'nvme', 'smart-log', device]
        output = subprocess.check_output(cmd)
        readings = [r for r in [self.values_from_line(line) for line in output.splitlines()] if r is not None]

        for reading in readings:
            if reading['name'] not in name_to_metric:
                continue

            value = reading['value']
            tags = base_tags + [
                'name:'+reading['name'],
            ]
            self.gauge(name_to_metric[reading['name']], value, tags=tags)

        return readings

    def check(self, instance):
        for device in instance['devices']:
            self.check_device(device, instance)

if __name__ == '__main__':
    check, instances = NVME.from_yaml('/etc/dd-agent/conf.d/nvme.yaml')
    for instance in instances:
        print "\nRunning the check against instance: %s" % (instance['host'])
        print check.check(instance)
